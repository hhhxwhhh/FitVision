import numpy as np
import random
from collections import defaultdict
from datetime import timedelta
import logging
from django.utils import timezone
from django.db.models import Count, Avg, F
from django.contrib.auth.models import User
from exercises.models import Exercise
from .models import UserInteraction, RecommendedExercise, UserState
from utils.vector_db import VectorDB
from .model_utils import DLModelManager
from .gnn_models import KnowledgeGraphGNN

# 高级算法库依赖
import torch
import torch.nn.functional as F_torch
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """推荐系统核心抽象类"""

    def recommend(self, user, limit=5):
        raise NotImplementedError


class KnowledgeGraphEngine(RecommendationEngine):
    """基于图神经网络 (GNN) 的知识图谱路径推荐"""

    def recommend(self, user, limit=5):
        # 1. 构建图结构
        exercises = list(
            Exercise.objects.filter(is_active=True).prefetch_related("prerequisites")
        )
        ex_id_to_idx = {ex.id: i for i, ex in enumerate(exercises)}
        num_nodes = len(exercises)

        if num_nodes == 0:
            return []

        # 2. 构造邻接矩阵 (归一化)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        adj = torch.eye(num_nodes).to(device)
        for ex in exercises:
            for pre in ex.prerequisites.all():
                if pre.id in ex_id_to_idx:
                    adj[ex_id_to_idx[pre.id], ex_id_to_idx[ex.id]] = 1.0

        # 归一化 D^-1/2 * A * D^-1/2
        rowsum = adj.sum(1)
        d_inv_sqrt = torch.pow(rowsum, -0.5).flatten()
        d_inv_sqrt[torch.isinf(d_inv_sqrt)] = 0.0
        d_mat_inv_sqrt = torch.diag(d_inv_sqrt)
        adj_norm = d_mat_inv_sqrt.mm(adj).mm(d_mat_inv_sqrt)

        # 3. 初始化 GNN 模型并进行推理
        model = KnowledgeGraphGNN(num_nodes=num_nodes, feature_dim=16).to(device)

        # 尝试加载预训练权重
        import os
        from django.conf import settings

        weights_path = os.path.join(
            settings.BASE_DIR, "recommendations", "weights", "gnn_model.pth"
        )
        if os.path.exists(weights_path):
            try:
                model.load_state_dict(torch.load(weights_path, map_location=device))
            except Exception as e:
                logger.warning("GNN weights load error: %s", e)
                return []
        else:
            logger.info("GNN weights not found, fallback to other engines")
            return []

        x_indices = torch.arange(num_nodes).to(device)

        with torch.no_grad():
            embeddings = model(x_indices, adj_norm)

        # 4. 基于用户历史寻找“下一个逻辑动作”
        history = list(
            UserInteraction.objects.filter(
                user=user, interaction_type="finish"
            ).order_by("-timestamp")[:3]
        )
        if not history:
            # 优化：预加载 count 避免 N+1
            start_nodes_query = (
                Exercise.objects.filter(is_active=True)
                .annotate(num_pre=Count("prerequisites"), num_unlocks=Count("unlocks"))
                .filter(num_pre=0)
                .order_by("-num_unlocks")[:limit]
            )

            return [
                (ex, 0.5 + (ex.num_unlocks / 10.0 if hasattr(ex, "num_unlocks") else 0))
                for ex in start_nodes_query
            ]

        # 计算历史动作嵌入的均值作为当前“知识状态”
        history_indices = [
            ex_id_to_idx[h.exercise_id]
            for h in history
            if h.exercise_id in ex_id_to_idx
        ]
        if not history_indices:
            return []

        user_knowledge_emb = embeddings[history_indices].mean(dim=0)

        # 5. 计算备选动作与用户知识状态的关联度
        # 优化：预加载关系
        unlocked_candidates = Exercise.objects.filter(
            prerequisites__id__in=[h.exercise_id for h in history]
        ).distinct()

        results = []
        for ex in unlocked_candidates:
            if ex.id in [h.exercise_id for h in history]:
                continue
            if ex.id not in ex_id_to_idx:
                continue
            idx = ex_id_to_idx[ex.id]
            # 使用 GNN 嵌入计算余弦相似度 + 路径分值 (注意这里改用 F_torch)
            sim = F_torch.cosine_similarity(
                user_knowledge_emb.unsqueeze(0), embeddings[idx].unsqueeze(0)
            ).item()
            results.append((ex, sim))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]


class ContentBasedEngine(RecommendationEngine):
    """基于语义向量的动作推荐"""

    def recommend(self, user, limit=5):
        # 1. 获取用户最近喜欢的动作
        recent_interactions = (
            UserInteraction.objects.filter(
                user=user, interaction_type__in=["like", "finish", "bookmark"]
            )
            .select_related("exercise")
            .order_by("-timestamp")[:3]
        )

        if not recent_interactions:
            return []

        # 2. 尝试使用向量数据库进行检索
        try:
            vdb = VectorDB()
            recommendations = []

            # 使用用户最近交互过的动作作为查询 query
            for interaction in recent_interactions:
                ex = interaction.exercise
                query_text = f"动作：{ex.name}。部位：{ex.get_target_muscle_display()}。描述：{ex.description}"

                results = vdb.collection.query(
                    query_texts=[query_text],
                    n_results=limit + 1,
                    where={"target_muscle": ex.target_muscle},  # 同部位推荐
                )

                # 处理结果
                if results and "ids" in results and results["ids"]:
                    candidate_ids = [
                        int(res_id)
                        for res_id in results["ids"][0]
                        if str(res_id).isdigit() and str(res_id) != str(ex.id)
                    ]
                    exercise_map = Exercise.objects.in_bulk(candidate_ids)

                    for i, res_id in enumerate(results["ids"][0]):
                        if res_id == str(ex.id):
                            continue  # 排除自身
                        # 距离越小分值越高
                        dist = (
                            results["distances"][0][i]
                            if "distances" in results
                            else 0.5
                        )
                        score = max(0.1, 1.0 - dist)
                        target_ex = (
                            exercise_map.get(int(res_id))
                            if str(res_id).isdigit()
                            else None
                        )
                        if target_ex:
                            recommendations.append((target_ex, score))

            # 去重并排序
            unique_recs = {}
            for ex, score in recommendations:
                if ex.id not in unique_recs or score > unique_recs[ex.id][1]:
                    unique_recs[ex.id] = (ex, score)

            return sorted(unique_recs.values(), key=lambda x: x[1], reverse=True)[
                :limit
            ]

        except Exception as e:
            print(f"VectorDB recommend error: {e}, falling back to rule-based...")
            # 3. 降级：基础属性匹配逻辑
            all_exercises = list(Exercise.objects.all())
            fallback_recs = []
            for interaction in recent_interactions:
                liked_ex = interaction.exercise
                sim_scores = []
                for ex in all_exercises:
                    if ex.id == liked_ex.id:
                        continue
                    score = 0
                    if ex.target_muscle == liked_ex.target_muscle:
                        score += 0.5
                    if ex.difficulty == liked_ex.difficulty:
                        score += 0.3
                    tags_overlap = set(ex.tags or []).intersection(
                        set(liked_ex.tags or [])
                    )
                    score += len(tags_overlap) * 0.1
                    sim_scores.append((ex, score))

                sim_scores.sort(key=lambda x: x[1], reverse=True)
                fallback_recs.extend(sim_scores[:limit])

            return sorted(fallback_recs, key=lambda x: x[1], reverse=True)[:limit]


class MLEngine(RecommendationEngine):
    """基于机器学习特征工程的个性化引擎"""

    def recommend(self, user, limit=5):
        profile = getattr(user, "profile", None)
        if not profile:
            return ColdStartEngine().recommend(user, limit)

        # 0. 基础过滤：排除跳过的动作
        ignored_ids = UserInteraction.objects.filter(
            user=user, interaction_type="skip"
        ).values_list("exercise_id", flat=True)

        exercises = Exercise.objects.exclude(id__in=ignored_ids)

        # 1. 构建用户多维特征向量 (User Persona Embedding)
        # 支持 BMI、体能等级、性别、年龄等动态权重计算
        level_map = {"beginner": 1, "intermediate": 3, "advanced": 5}
        user_feat = np.array(
            [
                (profile.bmi or 22.0) / 30.0,  # 归一化 BMI (默认为健康值)
                level_map.get(profile.fitness_level, 1) / 5.0,  # 归一化等级
                1.0 if profile.gender == "male" else 0.0,
                (profile.age or 25) / 100.0,
            ]
        )

        # 2. 权重矩阵 (基于专家经验训练后的静态模型权重)
        # 维度：(用户特征维度, 动作类型权重)
        weights = np.array(
            [
                [0.5, 0.2, 0.8],  # BMI 对应 [局部, 力量, 燃脂] 的影响力
                [0.2, 0.9, 0.1],  # Level 对应 [局部, 力量, 燃脂] 的影响力
                [0.1, 0.6, 0.3],  # 性别权重
                [0.1, 0.1, 0.1],  # 年龄权重
            ]
        )

        # 计算用户的实时偏好：[偏好局部, 偏好力量, 偏好燃脂]
        user_preference = np.dot(user_feat, weights)

        scored_exercises = []
        for ex in exercises:
            # 3. 提取动作特征
            # 简化的特征编码：[是否为局部, 是否为力量, 是否为全身燃脂]
            is_isolation = 1.0 if ex.target_muscle in ["arms", "abs"] else 0.0
            is_strength = 1.0 if ex.equipment != "none" else 0.5
            is_burn = 1.0 if ex.target_muscle == "full_body" else 0.2

            ex_feat = np.array([is_isolation, is_strength, is_burn])

            # 4. 计算得分 (向量点积)
            base_score = np.dot(user_preference, ex_feat)

            # 5. 难度匹配惩罚
            level_diff = abs(level_map.get(profile.fitness_level, 1) - ex.level)
            score = base_score * (1.0 - (level_diff * 0.15))

            # 6. 伤病硬核屏蔽
            if (
                profile.injury_history
                and ex.target_muscle in profile.injury_history.lower()
            ):
                score *= 0.1

            scored_exercises.append((ex, float(max(0.1, score))))

        scored_exercises.sort(key=lambda x: x[1], reverse=True)
        return scored_exercises[:limit]


class DLSequenceEngine(RecommendationEngine):
    """深度学习序列推荐引擎 (基于 GRU 神经网络)"""

    def recommend(self, user, limit=5):
        # 1. 获取用户最近的练习历史 (作为序列输入)
        history = list(
            UserInteraction.objects.filter(
                user=user, interaction_type="finish"
            ).order_by("-timestamp")[:5]
        )  # 取最近 5 个动作

        if not history:
            return []

        # 翻转顺序使其变为时间正序
        exercise_ids = [item.exercise_id for item in reversed(history)]

        # 2. 调用 DL 模型管理器进行推理
        try:
            model_manager = DLModelManager()
            predictions = model_manager.predict(exercise_ids, limit=limit)

            # 3. 结果组装
            recommendations = []
            pred_ids = [ex_id for ex_id, _ in predictions]
            exercise_map = Exercise.objects.in_bulk(pred_ids)
            for ex_id, score in predictions:
                ex = exercise_map.get(ex_id)
                if ex:
                    recommendations.append((ex, score))

            return recommendations
        except Exception as e:
            print(f"DL 推荐失效，降级至规则推荐: {e}")
            # 降级逻辑：简单部位关联
            last_ex = history[0].exercise
            complement_map = {
                "chest": ["arms", "shoulders"],
                "back": ["arms", "shoulders"],
                "legs": ["abs", "glutes"],
            }
            targets = complement_map.get(last_ex.target_muscle, ["full_body"])
            recs = Exercise.objects.filter(target_muscle__in=targets).exclude(
                id=last_ex.id
            )[:limit]
            return [(ex, 0.5) for ex in recs]


class RLAdaptiveEngine(RecommendationEngine):
    """自适应强化学习推荐引擎 (基于 Thompson Sampling 的多臂老虎机)"""

    def recommend(self, user, limit=5):
        state, _ = UserState.objects.get_or_create(user=user)

        # 1. 疲劳度过度保护逻辑
        if state.fatigue_level > 0.85:
            # 极高疲劳：只推荐拉伸/放松
            stretches = Exercise.objects.filter(tags__contains="stretching")[:limit]
            if not stretches:
                stretches = Exercise.objects.filter(difficulty="beginner")[:limit]
            return [(ex, 1.0) for ex in stretches]

        # 2. 部位避让逻辑 (Overuse Protection)
        one_day_ago = timezone.now() - timedelta(days=1)
        recent_muscles = list(
            UserInteraction.objects.filter(
                user=user, interaction_type="finish", timestamp__gte=one_day_ago
            )
            .values_list("exercise__target_muscle", flat=True)
            .distinct()
        )

        # 3. Thompson Sampling 核心逻辑
        # 我们将动作库视为多臂老虎机，每个动作的回报服从 Beta 分布
        # Alpha: 成功互动 (完成/喜欢), Beta: 消极互动 (不喜欢/跳过)
        all_exercises = Exercise.objects.exclude(target_muscle__in=recent_muscles)[
            :100
        ]  # 初步筛选

        # 批量获取用户互动统计
        interactions = UserInteraction.objects.filter(user=user).values(
            "exercise_id", "interaction_type"
        )
        stats_map = {}
        for inter in interactions:
            eid = inter["exercise_id"]
            if eid not in stats_map:
                stats_map[eid] = {"alpha": 1, "beta": 1}  # 初始先验分布 Beta(1,1)

            if inter["interaction_type"] in ["finish", "like"]:
                stats_map[eid]["alpha"] += 1
            elif inter["interaction_type"] == "dislike":
                stats_map[eid]["beta"] += 2  # 负面反馈权重更高

        scored_exercises = []
        for ex in all_exercises:
            stats = stats_map.get(ex.id, {"alpha": 1, "beta": 1})
            # 从 Beta 分布中采样
            score = np.random.beta(stats["alpha"], stats["beta"])

            # 针对目标强度的调节 (兼容新旧模型字段)
            target_intensity = getattr(state, "target_intensity", 5.0)
            if target_intensity:
                intensity_diff = abs(ex.calories_burned / 100 - target_intensity / 20)
                score *= 1 - min(intensity_diff, 0.5)

            scored_exercises.append((ex, float(score)))

        # 排序并取前 limit 个
        scored_exercises.sort(key=lambda x: x[1], reverse=True)
        return scored_exercises[:limit]


class ColdStartEngine(RecommendationEngine):
    """专家规则推荐引擎 (基于用户画像的分群冷启动)"""

    def recommend(self, user, limit=5):
        profile = getattr(user, "profile", None)
        user_level = profile.fitness_level if profile else "beginner"

        # 1. 获取全局高分热门动作
        # 统计最近 30 天内被用户完成或收藏的动作，按完成次数降序排列
        thirty_days_ago = timezone.now() - timedelta(days=30)
        popular_query = (
            UserInteraction.objects.filter(
                timestamp__gte=thirty_days_ago, interaction_type__in=["finish", "like"]
            )
            .values("exercise")
            .annotate(score=Count("id"))
            .order_by("-score")
        )

        # 2. 过滤掉不适合用户等级的动作
        # 初级用户仅可见初级动作，以此类推
        available_exercises = Exercise.objects.all()
        if user_level == "beginner":
            available_exercises = available_exercises.filter(difficulty="beginner")
        elif user_level == "intermediate":
            available_exercises = available_exercises.exclude(difficulty="advanced")

        available_ids = set(available_exercises.values_list("id", flat=True))

        # 3. 组合结果，应用多样性约束
        recs = []
        muscle_counts = {}

        popular_ids = [
            item["exercise"]
            for item in popular_query
            if item["exercise"] in available_ids
        ]
        exercise_map = Exercise.objects.in_bulk(popular_ids)

        for item in popular_query:
            ex_id = item["exercise"]
            if ex_id in available_ids:
                ex = exercise_map.get(ex_id)
                if not ex:
                    continue
                # 尽量保证多样化：每个部位最多推荐 2 个，防止内容过于单调
                count = muscle_counts.get(ex.target_muscle, 0)
                if count < 2:
                    recs.append((ex, 0.9))
                    muscle_counts[ex.target_muscle] = count + 1
            if len(recs) >= limit:
                break

        # 4. 兜底策略：根据用户目标偏好补全基础动作
        if len(recs) < limit:
            # 兼容性处理：UserProfile 暂时没有 goal 字段，使用 fitness_level 兜底
            goal = getattr(
                profile, "goal", profile.fitness_level if profile else "health"
            )
            remaining = limit - len(recs)
            # 优先从符合用户健身目标的动作中随机抽取
            # 如果没有找到匹配标签，则随机返回
            backups = available_exercises.filter(tags__contains=goal).order_by("?")[
                :remaining
            ]
            if not backups.exists():
                backups = available_exercises.order_by("?")[:remaining]
            for ex in backups:
                recs.append((ex, 0.6))

        return recs[:limit]


# 新增基于生命周期的时空穿梭 CF 引擎
class TimeTravelCFEngine(RecommendationEngine):
    """时空穿梭协同过滤：用成功老手的新手期经验指导当前新人"""

    def recommend(self, user, limit=5):
        profile = getattr(user, "profile", None)
        if not profile:
            return []

        # 1. 寻找“平行宇宙的你” (画像高度相似的用户群体)
        user_bmi = profile.bmi or 22.0

        # 跨表关联查询：直接用 User 模型，防止引包错误
        similar_users = User.objects.filter(
            profile__gender=profile.gender,
            profile__bmi__gte=user_bmi - 2.0,
            profile__bmi__lte=user_bmi + 2.0,
        ).exclude(id=user.id)

        # 如果有具体的目标(减脂/增肌)，进一步精确圈人
        if hasattr(profile, "goal") and profile.goal:
            similar_users = similar_users.filter(profile__goal=profile.goal)

        similar_user_ids = similar_users.values_list("id", flat=True)
        if not similar_user_ids:
            return []

        # 我们不仅找这些相似用户，还要限制只看他们【注册账号后的前 30 天内】的互动！
        time_travel_interactions = UserInteraction.objects.filter(
            user_id__in=similar_user_ids,
            interaction_type__in=["finish", "like"],
            # 穿越条件：互动时间 <= 该用户注册时间 + 30天
            timestamp__lte=F("user__date_joined") + timedelta(days=30),
            # 难度保护：只取适合当前用户的等级
            exercise__difficulty=profile.fitness_level or "beginner",
        )

        # 3. 统计这些动作在“老手新手期”的受欢迎程度
        cf_recommendations = (
            time_travel_interactions.values("exercise_id")
            .annotate(popularity=Count("id"))
            .order_by("-popularity")[: limit * 2]
        )

        # 4. 组装结果并打分
        recs = []
        seen_ids = set()
        for item in cf_recommendations:
            ex_id = item["exercise_id"]
            if ex_id not in seen_ids:
                try:
                    ex = Exercise.objects.get(id=ex_id)
                    # 分数计算：基础高分 0.8 + 流行度加成
                    score = min(0.8 + (item["popularity"] / 100.0), 0.98)
                    recs.append((ex, float(score)))
                    seen_ids.add(ex_id)
                except Exercise.DoesNotExist:
                    continue
            if len(recs) >= limit:
                break

        return recs


class HybridRecommender:
    """高级混合推荐调度器：支持多路召回、策略路由与结果持久化"""

    DEFAULT_ALGORITHMS = {
        "dl_sequence",
        "gnn_reasoning",
        "rl_adaptive",
        "ml_regression",
        "cosine",
        "popularity",
        "time_travel_cf",
    }

    SCENARIO_ENGINE_WEIGHTS = {
        "default": {
            "dl_sequence": 1.0,
            "gnn_reasoning": 0.9,
            "cosine": 0.85,
            "popularity": 0.7,
            "time_travel_cf": 0.95,
        },
        "discovery": {
            "gnn_reasoning": 1.0,
            "cosine": 0.95,
            "popularity": 0.6,
        },
        "daily_plan": {
            "ml_regression": 1.0,
            "popularity": 0.7,
        },
        "auto_adjust": {
            "rl_adaptive": 1.0,
            "popularity": 0.65,
        },
    }

    @staticmethod
    def _safe_score(value, default=0.5):
        try:
            score = float(value)
        except (TypeError, ValueError):
            return default
        if np.isnan(score) or np.isinf(score):
            return default
        return max(0.0, min(score, 1.2))

    @classmethod
    def _engine_weight(cls, scenario, engine):
        scene_weights = cls.SCENARIO_ENGINE_WEIGHTS.get(scenario, {})
        if engine in scene_weights:
            return scene_weights[engine]
        return cls.SCENARIO_ENGINE_WEIGHTS["default"].get(engine, 0.75)

    @staticmethod
    def _recent_blocked_ids(user, days=3):
        since = timezone.now() - timedelta(days=days)
        recent_actions = UserInteraction.objects.filter(
            user=user,
            timestamp__gte=since,
            interaction_type__in=["finish", "skip"],
        ).values_list("exercise_id", flat=True)

        seen_recent_recs = RecommendedExercise.objects.filter(
            user=user,
            is_seen=True,
            created_at__gte=since,
        ).values_list("exercise_id", flat=True)

        return set(recent_actions).union(set(seen_recent_recs))

    @classmethod
    def _blend_sources(cls, rec_sources, scenario, blocked_ids):
        merged = {}
        for ex, raw_score, algo in rec_sources:
            if not ex or ex.id in blocked_ids:
                continue

            score = cls._safe_score(raw_score)
            weighted = score * cls._engine_weight(scenario, algo)

            if ex.id not in merged:
                merged[ex.id] = {
                    "ex": ex,
                    "score": weighted,
                    "sources": {algo},
                    "algorithm": algo,
                    "best_weighted": weighted,
                }
                continue

            merged_item = merged[ex.id]
            merged_item["score"] += weighted
            merged_item["sources"].add(algo)
            if weighted > merged_item["best_weighted"]:
                merged_item["best_weighted"] = weighted
                merged_item["algorithm"] = algo

        candidates = []
        for item in merged.values():
            source_bonus = min(0.05 * len(item["sources"]), 0.2)
            item["score"] = item["score"] + source_bonus
            candidates.append(item)

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates

    @staticmethod
    def _rerank_with_diversity(candidates, limit):
        if not candidates:
            return []

        pending = list(candidates)
        selected = []
        muscle_counter = defaultdict(int)

        while pending and len(selected) < limit:
            best_idx = 0
            best_adjusted = -1.0

            # 限制扫描窗口，兼顾质量与性能
            for idx, item in enumerate(pending[:40]):
                muscle = getattr(item["ex"], "target_muscle", "unknown") or "unknown"
                diversity_penalty = 0.12 * muscle_counter[muscle]
                adjusted = item["score"] - diversity_penalty
                if adjusted > best_adjusted:
                    best_adjusted = adjusted
                    best_idx = idx

            chosen = pending.pop(best_idx)
            chosen["score"] = max(0.0, best_adjusted)
            selected.append(chosen)
            muscle = getattr(chosen["ex"], "target_muscle", "unknown") or "unknown"
            muscle_counter[muscle] += 1

        return selected

    @staticmethod
    def _compute_exploration_ratio(positive_count, negative_count, default=0.18):
        total = positive_count + negative_count
        if total <= 0:
            return default

        negative_ratio = negative_count / total
        adaptive = default + (negative_ratio - 0.4) * 0.35
        return max(0.08, min(0.35, adaptive))

    @staticmethod
    def _select_with_exploration(candidates, limit, exploration_ratio, rng=None):
        if not candidates or limit <= 0:
            return []
        if len(candidates) <= limit:
            return candidates[:limit]

        rng = rng or random
        # 探索槽位不超过总数的一半，避免推荐质量明显下降
        explore_slots = min(limit // 2, int(round(limit * exploration_ratio)))
        exploit_slots = max(limit - explore_slots, 1)

        exploit_part = candidates[:exploit_slots]
        if explore_slots <= 0:
            return exploit_part[:limit]

        explore_pool = candidates[exploit_slots:]
        if not explore_pool:
            return exploit_part[:limit]

        pick_n = min(explore_slots, len(explore_pool))
        if len(explore_pool) <= pick_n:
            explore_pick = list(explore_pool)
        else:
            explore_pick = rng.sample(explore_pool, pick_n)

        merged = exploit_part + explore_pick
        merged.sort(key=lambda x: x["score"], reverse=True)
        return merged[:limit]

    @staticmethod
    def get_recommendations(user, scenario="default", limit=6):
        reason_map = {
            "dl_sequence": "根据您的练习序列预测",
            "gnn_reasoning": "基于训练路径的逻辑进阶",
            "rl_adaptive": "基于您的身体状态实时调节",
            "ml_regression": "基于您的身体指标定制",
            "cosine": "基于您相似的互动偏好",
            "popularity": "社区高热度动作",
            "time_travel_cf": "与您体质相似的进阶者在新手期最爱的动作",
        }

        # 1. 缓存/持久化检查：如果过去 6 小时内已经为该场景生成过充分的推荐，则直接返回
        six_hours_ago = timezone.now() - timedelta(hours=6)
        existing_recs = RecommendedExercise.objects.filter(
            user=user,
            created_at__gte=six_hours_ago,
        )
        if scenario == "default":
            existing_recs = existing_recs.filter(
                algorithm__in=HybridRecommender.DEFAULT_ALGORITHMS
            )
        else:
            existing_recs = existing_recs.filter(algorithm__startswith=f"{scenario}:")
        existing_recs = existing_recs.order_by("rank")

        if existing_recs.count() >= limit:
            return existing_recs[:limit]

        rec_sources = []

        history_count = UserInteraction.objects.filter(
            user=user, interaction_type="finish"
        ).count()
        is_newbie = history_count < 10  # 完成动作少于 10 个即为新手

        try:
            if is_newbie:
                # 纯新手：强制激活“时空穿梭 CF”
                print(f"检测到新手用户 {user.username}，启动时空穿梭协同过滤...")
                try:
                    sources_cf = TimeTravelCFEngine().recommend(user, limit=limit)
                    rec_sources.extend(
                        [(ex, s, "time_travel_cf") for ex, s in sources_cf]
                    )
                except Exception as e:
                    print(f"CF Engine Error: {e}")

            elif scenario == "auto_adjust":
                # 强化学习主导：自适应疲劳和表现
                sources = RLAdaptiveEngine().recommend(user, limit=limit)
                rec_sources.extend([(ex, s, "rl_adaptive") for ex, s in sources])
            elif scenario == "discovery":
                # 内容/知识图谱主导：发现新领域
                sources_gnn = KnowledgeGraphEngine().recommend(user, limit=limit // 2)
                rec_sources.extend([(ex, s, "gnn_reasoning") for ex, s in sources_gnn])
                sources_cb = ContentBasedEngine().recommend(user, limit=limit // 2)
                rec_sources.extend([(ex, s, "cosine") for ex, s in sources_cb])
            elif scenario == "daily_plan":
                # 机器学习主导：计划性较强
                sources = MLEngine().recommend(user, limit=limit)
                rec_sources.extend([(ex, s, "ml_regression") for ex, s in sources])
            else:
                # 默认/混合策略：多路召回
                try:
                    sources_dl = DLSequenceEngine().recommend(user, limit=3)
                    rec_sources.extend([(ex, s, "dl_sequence") for ex, s in sources_dl])
                except Exception as e:
                    print(f"DL Engine Error: {e}")

                try:
                    sources_gnn = KnowledgeGraphEngine().recommend(user, limit=2)
                    rec_sources.extend(
                        [(ex, s, "gnn_reasoning") for ex, s in sources_gnn]
                    )
                except Exception as e:
                    print(f"GNN Engine Error: {e}")

                try:
                    sources_cb = ContentBasedEngine().recommend(user, limit=2)
                    rec_sources.extend([(ex, s, "cosine") for ex, s in sources_cb])
                except Exception as e:
                    print(f"Cosine Engine Error: {e}")
        except Exception as e:
            print(f"推荐场景 [{scenario}] 执行异常: {e}")

        # 3. 分数融合 + 去重 + 多样性重排
        blocked_ids = HybridRecommender._recent_blocked_ids(user)
        fused_candidates = HybridRecommender._blend_sources(
            rec_sources, scenario=scenario, blocked_ids=blocked_ids
        )

        reranked_candidates = HybridRecommender._rerank_with_diversity(
            fused_candidates, limit=max(limit * 3, limit)
        )
        candidate_pool = list(reranked_candidates)
        seen_ids = {item["ex"].id for item in candidate_pool}

        # 4. 兜底策略：如果召回不足，使用热门冷启动补全
        if len(candidate_pool) < limit:
            remaining = limit - len(candidate_pool)
            backups = ColdStartEngine().recommend(user, limit=remaining * 2)
            for ex, score in backups:
                if ex.id not in seen_ids and ex.id not in blocked_ids:
                    candidate_pool.append(
                        {"ex": ex, "score": score, "algorithm": "popularity"}
                    )
                    seen_ids.add(ex.id)
                if len(candidate_pool) >= limit * 2:
                    break

        # 5. 自适应探索：近期负反馈越高，探索比重越大
        recent_feedback = UserInteraction.objects.filter(
            user=user,
            timestamp__gte=timezone.now() - timedelta(days=14),
            interaction_type__in=["finish", "like", "bookmark", "skip"],
        ).values_list("interaction_type", flat=True)

        positive_count = 0
        negative_count = 0
        for action in recent_feedback:
            if action in ["finish", "like", "bookmark"]:
                positive_count += 1
            elif action == "skip":
                negative_count += 1

        exploration_ratio = HybridRecommender._compute_exploration_ratio(
            positive_count=positive_count,
            negative_count=negative_count,
        )

        final_recs = HybridRecommender._select_with_exploration(
            candidate_pool,
            limit=limit,
            exploration_ratio=exploration_ratio,
        )

        # 6. 结果持久化与理由生成
        results = []
        # 清理该场景下的旧推荐
        old_recs = RecommendedExercise.objects.filter(user=user)
        if scenario == "default":
            old_recs = old_recs.filter(
                algorithm__in=HybridRecommender.DEFAULT_ALGORITHMS
            )
        else:
            old_recs = old_recs.filter(algorithm__startswith=f"{scenario}:")
        old_recs.delete()

        for i, item in enumerate(final_recs[:limit]):
            # 记录推荐来源和场景标识，用于持久化过滤
            algo_tag = (
                f"{scenario}:{item['algorithm']}"
                if scenario != "default"
                else item["algorithm"]
            )

            rec_obj = RecommendedExercise.objects.create(
                user=user,
                exercise=item["ex"],
                algorithm=algo_tag,
                score=item["score"],
                rank=i + 1,
                reason=reason_map.get(item["algorithm"], "AI 智能推荐"),
            )
            results.append(rec_obj)

        return results
