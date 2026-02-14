import numpy as np
import random
from datetime import datetime, timedelta
from django.db.models import Count, Avg
from django.contrib.auth.models import User
from exercises.models import Exercise
from .models import UserInteraction, RecommendedExercise, UserState
from utils.vector_db import VectorDB

# 模拟算法库 (实际生产环境需安装 sklearn, torch 等)
try:
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.feature_extraction.text import TfidfVectorizer
except ImportError:
    cosine_similarity = None
    TfidfVectorizer = None

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
    """高级特征加权引擎 (模拟线性回归/分类决策)"""
    def recommend(self, user, limit=5):
        profile = getattr(user, 'profile', None)
        if not profile:
            return ColdStartEngine().recommend(user, limit)
            
        # 0. 排除用户明确表示不喜欢的
        ignored_ids = UserInteraction.objects.filter(
            user=user, 
            interaction_type='skip'
        ).values_list('exercise_id', flat=True)
        
        all_exercises = Exercise.objects.exclude(id__in=ignored_ids)
        scored_exercises = []
        
        # 获取用户伤病历史
        injury_info = profile.injury_history.lower()
        
        for ex in all_exercises:
            score = 50.0 # 基础分
            
            # 1. 难度适配 (Level 1-5)
            # 用户等级转换: beginner(1), intermediate(3), advanced(5)
            level_map = {'beginner': 1, 'intermediate': 3, 'advanced': 5}
            user_lv = level_map.get(profile.fitness_level, 1)
            score += (5 - abs(user_lv - ex.level)) * 5
            
            # 2. 伤病避让
            if ex.target_muscle in injury_info:
                score -= 40 # 极大幅度降权
            
            # 3. BMI & 燃脂需求
            if profile.bmi > 25:
                # 高BMI用户更倾向于全身/大肌群燃脂
                if ex.target_muscle in ['full_body', 'legs']:
                    score += 10
            elif profile.bmi < 18.5:
                # 低BMI用户倾向于局部增肌
                if ex.target_muscle not in ['full_body']:
                    score += 5
            
            # 4. 性别偏好 (统计学模拟)
            if profile.gender == 'female' and ex.target_muscle in ['glutes', 'abs']:
                score += 8
            if profile.gender == 'male' and ex.target_muscle in ['chest', 'back', 'arms']:
                score += 8
                
            # 5. 器材加分 (如果有器械则权重稍高，假设用户有基础器械)
            if ex.equipment != 'none':
                score += 2
                
            scored_exercises.append((ex, score / 100.0))
            
        scored_exercises.sort(key=lambda x: x[1], reverse=True)
        return scored_exercises[:limit]

class DLSequenceEngine(RecommendationEngine):
    """序列关联推荐引擎 (基于全站转移概率模拟)"""
    def recommend(self, user, limit=5):
        # 1. 获取用户最近的一次练习动作
        last_interaction = UserInteraction.objects.filter(
            user=user, 
            interaction_type='finish'
        ).order_by('-timestamp').first()
        
        if not last_interaction:
            return []
            
        last_ex = last_interaction.exercise
        
        # 2. 定义解剖学关联（模拟转移矩阵）
        # 练完主干部位后通常接的互补部位
        complement_map = {
            'chest': ['arms', 'shoulders', 'abs'],
            'back': ['arms', 'shoulders', 'abs'],
            'legs': ['abs', 'glutes', 'full_body'],
            'shoulders': ['arms', 'chest'],
            'arms': ['abs', 'full_body']
        }
        
        # 3. 寻找潜在候选项
        possible_targets = complement_map.get(last_ex.target_muscle, ['full_body'])
        
        # 获取关联推荐
        recs = Exercise.objects.filter(
            target_muscle__in=possible_targets
        ).exclude(id=last_ex.id).order_by('?')[:limit]
        
        # 4. 模拟序列概率分值
        weighted_recs = []
        for i, ex in enumerate(recs):
            # 基础分随排名递减
            score = 0.9 - (i * 0.1)
            weighted_recs.append((ex, score))
            
        return weighted_recs
        
class RLAdaptiveEngine(RecommendationEngine):
    """自适应状态推荐引擎 (状态机 + Thompson Sampling 模拟)"""
    def recommend(self, user, limit=5):
        state, _ = UserState.objects.get_or_create(user=user)
        recent_interactions = UserInteraction.objects.filter(user=user).order_by('-timestamp')[:10]
        
        # 1. 疲劳度过度保护逻辑
        if state.fatigue_level > 0.85:
            # 极高疲劳：只推荐拉伸/放松 (假设 tags 含 'stretch')
            stretches = Exercise.objects.filter(tags__contains='stretching')[:limit]
            if not stretches:
                stretches = Exercise.objects.filter(difficulty='beginner')[:limit]
            return [(ex, 1.0) for ex in stretches]
            
        # 2. 部位避让逻辑 (Overuse Protection)
        # 找出过去 24 小时练得最多的部位
        one_day_ago = datetime.now() - timedelta(days=1)
        recent_muscles = UserInteraction.objects.filter(
            user=user, 
            interaction_type='finish',
            timestamp__gte=one_day_ago
        ).values_list('exercise__target_muscle', flat=True)
        
        # 3. 探索 vs 利用 (Exploration vs Exploitation)
        # 模拟 Epsilon-Greedy
        if random.random() < 0.3: # 30% 探索新领域
            # 探索：用户没练过，且不是最近练过的部位
            explored = Exercise.objects.exclude(
                id__in=UserInteraction.objects.filter(user=user).values_list('exercise_id', flat=True)
            ).exclude(
                target_muscle__in=list(set(recent_muscles))
            ).order_by('?')[:limit]
            return [(ex, 0.75) for ex in explored]
            
        # 利用：历史表现好的推荐
        best_past = UserInteraction.objects.filter(
            user=user, 
            interaction_type__in=['like', 'finish']
        ).values('exercise').annotate(
            avg_val=Avg('score')
        ).order_by('-avg_val')[:limit]
        
        results = []
        for item in best_past:
            ex = Exercise.objects.get(id=item['exercise'])
            # 如果是最近刚练过的部位，分值打折
            final_score = item['avg_val']
            if ex.target_muscle in recent_muscles:
                final_score *= 0.5
            results.append((ex, final_score))
            
        # 排序并补足
        results.sort(key=lambda x: x[1], reverse=True)
        if len(results) < limit:
            remaining = limit - len(results)
            backups = MLEngine().recommend(user, limit=remaining)
            results.extend(backups)
            
        return results[:limit]

class ColdStartEngine(RecommendationEngine):
    """高级冷启动推荐 (基于分群热门和专家规则)"""
    def recommend(self, user, limit=5):
        profile = getattr(user, 'profile', None)
        user_level = profile.fitness_level if profile else 'beginner'
        
        # 1. 获取最近 30 天的热门动作 (时间加权模拟)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        popular_query = UserInteraction.objects.filter(
            timestamp__gte=thirty_days_ago
        ).values('exercise').annotate(
            score=Count('id')
        ).order_by('-score')
        
        # 2. 过滤掉不适合用户等级的动作 (粗筛)
        # 假设：beginner 只能做 developer/beginner，大神可以做所有
        available_exercises = Exercise.objects.all()
        if user_level == 'beginner':
            available_exercises = available_exercises.filter(difficulty='beginner')
        elif user_level == 'intermediate':
            available_exercises = available_exercises.exclude(difficulty='advanced')
            
        available_ids = set(available_exercises.values_list('id', flat=True))
        
        # 3. 组合热门结果
        recs = []
        seen_muscles = set()
        
        for item in popular_query:
            ex_id = item['exercise']
            if ex_id in available_ids:
                ex = Exercise.objects.get(id=ex_id)
                # 尽量保证多样化：每个部位最多推荐 2 个
                if seen_muscles.count(ex.target_muscle) < 2:
                    recs.append((ex, 0.85))
                    seen_muscles.add(ex.target_muscle)
            if len(recs) >= limit:
                break
                
        # 4. 兜底：如果热门不足，按部位补全基础动作
        if len(recs) < limit:
            backups = available_exercises.order_by('?')[:limit - len(recs)]
            for ex in backups:
                recs.append((ex, 0.5))
        
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
