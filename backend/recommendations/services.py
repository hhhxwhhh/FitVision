import numpy as np
import random
from datetime import datetime, timedelta
from django.db.models import Count, Avg
from django.contrib.auth.models import User
from exercises.models import Exercise
from .models import UserInteraction, RecommendedExercise, UserState
from utils.vector_db import VectorDB
from .model_utils import DLModelManager

# 高级算法库依赖
import torch
from sklearn.metrics.pairwise import cosine_similarity

class RecommendationEngine:
    """推荐系统核心抽象类"""
    def recommend(self, user, limit=5):
        raise NotImplementedError

class ContentBasedEngine(RecommendationEngine):
    """基于语义向量的动作推荐"""
    def recommend(self, user, limit=5):
        # 1. 获取用户最近喜欢的动作
        recent_interactions = UserInteraction.objects.filter(
            user=user, 
            interaction_type__in=['like', 'finish', 'bookmark']
        ).select_related('exercise').order_by('-timestamp')[:3]
        
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
                    where={"target_muscle": ex.target_muscle} # 同部位推荐
                )
                
                # 处理结果
                if results and 'ids' in results and results['ids']:
                    for i, res_id in enumerate(results['ids'][0]):
                        if res_id == str(ex.id): continue # 排除自身
                        # 距离越小分值越高
                        dist = results['distances'][0][i] if 'distances' in results else 0.5
                        score = max(0.1, 1.0 - dist) 
                        try:
                            target_ex = Exercise.objects.get(id=res_id)
                            recommendations.append((target_ex, score))
                        except Exercise.DoesNotExist:
                            continue
            
            # 去重并排序
            unique_recs = {}
            for ex, score in recommendations:
                if ex.id not in unique_recs or score > unique_recs[ex.id][1]:
                    unique_recs[ex.id] = (ex, score)
            
            return sorted(unique_recs.values(), key=lambda x: x[1], reverse=True)[:limit]

        except Exception as e:
            print(f"VectorDB recommend error: {e}, falling back to rule-based...")
            # 3. 降级：基础属性匹配逻辑
            all_exercises = list(Exercise.objects.all())
            fallback_recs = []
            for interaction in recent_interactions:
                liked_ex = interaction.exercise
                sim_scores = []
                for ex in all_exercises:
                    if ex.id == liked_ex.id: continue
                    score = 0
                    if ex.target_muscle == liked_ex.target_muscle: score += 0.5
                    if ex.difficulty == liked_ex.difficulty: score += 0.3
                    tags_overlap = set(ex.tags or []).intersection(set(liked_ex.tags or []))
                    score += len(tags_overlap) * 0.1
                    sim_scores.append((ex, score))
                
                sim_scores.sort(key=lambda x: x[1], reverse=True)
                fallback_recs.extend(sim_scores[:limit])
            
            return sorted(fallback_recs, key=lambda x: x[1], reverse=True)[:limit]

class MLEngine(RecommendationEngine):
    """基于机器学习特征工程的个性化引擎"""
    def recommend(self, user, limit=5):
        profile = getattr(user, 'profile', None)
        if not profile:
            return ColdStartEngine().recommend(user, limit)
            
        # 0. 基础过滤：排除跳过的动作
        ignored_ids = UserInteraction.objects.filter(
            user=user, 
            interaction_type='skip'
        ).values_list('exercise_id', flat=True)
        
        exercises = Exercise.objects.exclude(id__in=ignored_ids)
        
        # 1. 构建用户多维特征向量 (User Persona Embedding)
        # 支持 BMI、体能等级、性别、年龄等动态权重计算
        level_map = {'beginner': 1, 'intermediate': 3, 'advanced': 5}
        user_feat = np.array([
            profile.bmi / 30.0,  # 归一化 BMI
            level_map.get(profile.fitness_level, 1) / 5.0, # 归一化等级
            1.0 if profile.gender == 'male' else 0.0,
            profile.age / 100.0
        ])
        
        # 2. 权重矩阵 (基于专家经验训练后的静态模型权重)
        # 维度：(用户特征维度, 动作类型权重)
        weights = np.array([
            [0.5, 0.2, 0.8], # BMI 对应 [局部, 力量, 燃脂] 的影响力
            [0.2, 0.9, 0.1], # Level 对应 [局部, 力量, 燃脂] 的影响力
            [0.1, 0.6, 0.3], # 性别权重
            [0.1, 0.1, 0.1], # 年龄权重
        ])
        
        # 计算用户的实时偏好：[偏好局部, 偏好力量, 偏好燃脂]
        user_preference = np.dot(user_feat, weights)
        
        scored_exercises = []
        for ex in exercises:
            # 3. 提取动作特征
            # 简化的特征编码：[是否为局部, 是否为力量, 是否为全身燃脂]
            is_isolation = 1.0 if ex.target_muscle in ['arms', 'abs'] else 0.0
            is_strength = 1.0 if ex.equipment != 'none' else 0.5
            is_burn = 1.0 if ex.target_muscle == 'full_body' else 0.2
            
            ex_feat = np.array([is_isolation, is_strength, is_burn])
            
            # 4. 计算得分 (向量点积)
            base_score = np.dot(user_preference, ex_feat)
            
            # 5. 难度匹配惩罚
            level_diff = abs(level_map.get(profile.fitness_level, 1) - ex.level)
            score = base_score * (1.0 - (level_diff * 0.15))
            
            # 6. 伤病硬核屏蔽
            if profile.injury_history and ex.target_muscle in profile.injury_history.lower():
                score *= 0.1
                
            scored_exercises.append((ex, max(0, score)))
            
        scored_exercises.sort(key=lambda x: x[1], reverse=True)
        return scored_exercises[:limit]

class DLSequenceEngine(RecommendationEngine):
    """深度学习序列推荐引擎 (基于 GRU 神经网络)"""
    def recommend(self, user, limit=5):
        # 1. 获取用户最近的练习历史 (作为序列输入)
        history = UserInteraction.objects.filter(
            user=user, 
            interaction_type='finish'
        ).order_by('-timestamp')[:5] # 取最近 5 个动作
        
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
            for ex_id, score in predictions:
                try:
                    ex = Exercise.objects.get(id=ex_id)
                    recommendations.append((ex, score))
                except Exercise.DoesNotExist:
                    continue
                    
            return recommendations
        except Exception as e:
            print(f"DL 推荐失效，降级至规则推荐: {e}")
            # 降级逻辑：简单部位关联
            last_ex = history[0].exercise
            complement_map = {
                'chest': ['arms', 'shoulders'],
                'back': ['arms', 'shoulders'],
                'legs': ['abs', 'glutes']
            }
            targets = complement_map.get(last_ex.target_muscle, ['full_body'])
            recs = Exercise.objects.filter(target_muscle__in=targets).exclude(id=last_ex.id)[:limit]
            return [(ex, 0.5) for ex in recs]
        
class RLAdaptiveEngine(RecommendationEngine):
    """自适应强化学习推荐引擎 (基于 Thompson Sampling 的多臂老虎机)"""
    def recommend(self, user, limit=5):
        state, _ = UserState.objects.get_or_create(user=user)
        
        # 1. 疲劳度过度保护逻辑
        if state.fatigue_level > 0.85:
            # 极高疲劳：只推荐拉伸/放松
            stretches = Exercise.objects.filter(tags__contains='stretching')[:limit]
            if not stretches:
                stretches = Exercise.objects.filter(difficulty='beginner')[:limit]
            return [(ex, 1.0) for ex in stretches]
            
        # 2. 部位避让逻辑 (Overuse Protection)
        one_day_ago = datetime.now() - timedelta(days=1)
        recent_muscles = list(UserInteraction.objects.filter(
            user=user, 
            interaction_type='finish',
            timestamp__gte=one_day_ago
        ).values_list('exercise__target_muscle', flat=True).distinct())
        
        # 3. Thompson Sampling 核心逻辑
        # 我们将动作库视为多臂老虎机，每个动作的回报服从 Beta 分布
        # Alpha: 成功互动 (完成/喜欢), Beta: 消极互动 (不喜欢/跳过)
        all_exercises = Exercise.objects.exclude(target_muscle__in=recent_muscles)[:100] # 初步筛选
        
        # 批量获取用户互动统计
        interactions = UserInteraction.objects.filter(user=user).values('exercise_id', 'interaction_type')
        stats_map = {}
        for inter in interactions:
            eid = inter['exercise_id']
            if eid not in stats_map:
                stats_map[eid] = {'alpha': 1, 'beta': 1} # 初始先验分布 Beta(1,1)
            
            if inter['interaction_type'] in ['finish', 'like']:
                stats_map[eid]['alpha'] += 1
            elif inter['interaction_type'] == 'dislike':
                stats_map[eid]['beta'] += 2 # 负面反馈权重更高
        
        scored_exercises = []
        for ex in all_exercises:
            stats = stats_map.get(ex.id, {'alpha': 1, 'beta': 1})
            # 从 Beta 分布中采样
            score = np.random.beta(stats['alpha'], stats['beta'])
            
            # 针对目标强度的调节
            if state.target_intensity:
                intensity_diff = abs(ex.calories_burned / 100 - state.target_intensity / 20)
                score *= (1 - min(intensity_diff, 0.5))
                
            scored_exercises.append((ex, float(score)))
            
        # 排序并取前 limit 个
        scored_exercises.sort(key=lambda x: x[1], reverse=True)
        return scored_exercises[:limit]

class ColdStartEngine(RecommendationEngine):
    """专家规则推荐引擎 (基于用户画像的分群冷启动)"""
    def recommend(self, user, limit=5):
        profile = getattr(user, 'profile', None)
        user_level = profile.fitness_level if profile else 'beginner'
        
        # 1. 获取全局高分热门动作
        # 统计最近 30 天内被用户完成或收藏的动作，按完成次数降序排列
        thirty_days_ago = datetime.now() - timedelta(days=30)
        popular_query = UserInteraction.objects.filter(
            timestamp__gte=thirty_days_ago,
            interaction_type__in=['finish', 'like']
        ).values('exercise').annotate(
            score=Count('id')
        ).order_by('-score')
        
        # 2. 过滤掉不适合用户等级的动作
        # 初级用户仅可见初级动作，以此类推
        available_exercises = Exercise.objects.all()
        if user_level == 'beginner':
            available_exercises = available_exercises.filter(difficulty='beginner')
        elif user_level == 'intermediate':
            available_exercises = available_exercises.exclude(difficulty='advanced')
            
        available_ids = set(available_exercises.values_list('id', flat=True))
        
        # 3. 组合结果，应用多样性约束
        recs = []
        muscle_counts = {}
        
        for item in popular_query:
            ex_id = item['exercise']
            if ex_id in available_ids:
                ex = Exercise.objects.get(id=ex_id)
                # 尽量保证多样化：每个部位最多推荐 2 个，防止内容过于单调
                count = muscle_counts.get(ex.target_muscle, 0)
                if count < 2:
                    recs.append((ex, 0.9))
                    muscle_counts[ex.target_muscle] = count + 1
            if len(recs) >= limit:
                break
                
        # 4. 兜底策略：根据用户目标偏好补全基础动作
        if len(recs) < limit:
            goal = profile.goal if profile else 'health'
            remaining = limit - len(recs)
            # 优先从符合用户健身目标的动作中随机抽取
            backups = available_exercises.filter(tags__contains=goal).order_by('?')[:remaining]
            for ex in backups:
                recs.append((ex, 0.6))
        
        return recs[:limit]

class HybridRecommender:
    """高级混合推荐调度器：负责召回过滤与结果持久化"""
    
    @staticmethod
    def get_recommendations(user, scenario='default', limit=6):
        # 1. 持久化检查：如果过去 6 小时内已经为该场景生成过推荐，则直接返回
        # 这样可以保证推荐结果的稳定性，直到用户主动触发变化或时间到期
        six_hours_ago = datetime.now() - timedelta(hours=6)
        existing_recs = RecommendedExercise.objects.filter(
            user=user,
            created_at__gte=six_hours_ago
        ).order_by('rank')
        
        # 对于默认场景，如果已经有至少 3 条推荐，暂时不更新以节省资源
        if scenario == 'default' and existing_recs.count() >= 3:
            return existing_recs[:limit]

        # 2. 策略路由选择
        interaction_count = UserInteraction.objects.filter(user=user).count()
        
        # 实时状态感知：如果疲劳度极高，强制触发状态感知逻辑
        state, _ = UserState.objects.get_or_create(user=user)
        if state.fatigue_level > 0.8 and scenario != 'discovery':
            scenario = 'auto_adjust'

        # 默认引擎选择逻辑
        if interaction_count < 3 and scenario == 'default':
            engine = ColdStartEngine()
            algo_name = 'popularity'
        elif scenario == 'discovery':
            engine = ContentBasedEngine()
            algo_name = 'cosine'
        elif scenario == 'daily_plan':
            engine = MLEngine()
            algo_name = 'ml_regression'
        elif scenario == 'auto_adjust':
            engine = RLAdaptiveEngine()
            algo_name = 'rl_adaptive'
        else:
            # 混合策略：尝试 DL 序列
            engine = DLSequenceEngine()
            algo_name = 'dl_sequence'

        # 3. 执行推荐召回
        raw_recs = engine.recommend(user, limit=limit)
        
        # 降级处理
        if not raw_recs and algo_name != 'popularity':
            raw_recs = ColdStartEngine().recommend(user, limit=limit)
            algo_name = 'popularity (fallback)'

        # 4. 存储并持久化结果
        processed_recs = []
        # 清理该用户在该场景下的过时结果 (可选)
        # RecommendedExercise.objects.filter(user=user, algorithm=algo_name[:20]).delete()
        
        for rank, item in enumerate(raw_recs, 1):
            ex, score = item
            # 根据算法类型生成持久化的推荐理由
            reason_map = {
                'cosine': f"发现与您喜欢的动作相似的 {ex.name}",
                'ml_regression': f"基于您的 BMI 和健身等级定制",
                'dl_sequence': f"根据您的练习历史，下一组建议进行这个",
                'rl_adaptive': f"检测到您的疲劳状态，已为您切换为低强度训练",
                'popularity': f"大家都在练的入门动作"
            }
            
            rec_obj = RecommendedExercise.objects.create(
                user=user,
                exercise=ex,
                algorithm=algo_name[:20],
                score=float(score),
                rank=rank,
                reason=reason_map.get(algo_name.split(' ')[0], "AI 为您推荐")
            )
            processed_recs.append(rec_obj)
            
        return processed_recs
