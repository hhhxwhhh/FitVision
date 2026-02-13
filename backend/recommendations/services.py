import numpy as np
import random
from datetime import datetime, timedelta
from django.db.models import Count, Avg
from django.contrib.auth.models import User
from exercises.models import Exercise
from .models import UserInteraction, RecommendedExercise, UserState

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
    """基于余弦相似度的内容推荐"""
    def recommend(self, user, limit=5):
        # 1. 获取用户最近喜欢的动作
        recent_likes = UserInteraction.objects.filter(
            user=user, 
            interaction_type='like'
        ).values_list('exercise_id', flat=True)[:3]
        
        if not recent_likes:
            return []

        all_exercises = list(Exercise.objects.all())
        # 这里简化处理：基于目标肌群和难度计算相似度
        # 实际开发中会使用 TF-IDF 处理 tags 和 description
        recommendations = []
        for liked_id in recent_likes:
            liked_ex = Exercise.objects.get(id=liked_id)
            sim_scores = []
            for ex in all_exercises:
                if ex.id == liked_id: continue
                score = 0
                if ex.target_muscle == liked_ex.target_muscle: score += 0.5
                if ex.difficulty == liked_ex.difficulty: score += 0.3
                # 标签重合度
                tags_overlap = set(ex.tags).intersection(set(liked_ex.tags))
                score += len(tags_overlap) * 0.1
                sim_scores.append((ex, score))
            
            sim_scores.sort(key=lambda x: x[1], reverse=True)
            recommendations.extend(sim_scores[:limit])
        
        return sorted(recommendations, key=lambda x: x[1], reverse=True)[:limit]

class MLEngine(RecommendationEngine):
    """机器学习预测引擎 (Random Forest 模拟)"""
    def recommend(self, user, limit=5):
        # 预测用户可能给该动作的评分
        # 特征：用户BMI, 健身等级, 动作难度, 动作类型
        profile = user.profile
        all_exercises = Exercise.objects.all()
        scored_exercises = []
        
        for ex in all_exercises:
            # 基础分：难度适配度
            score = 100
            diff_map = {'beginner': 1, 'intermediate': 2, 'advanced': 3}
            user_lv = diff_map.get(profile.fitness_level, 1)
            ex_lv = diff_map.get(ex.difficulty, 1)
            
            score -= abs(user_lv - ex_lv) * 20
            
            # 目标契合度
            if profile.bmi > 25 and ex.target_muscle == 'full_body':
                score += 15 # 大体重更推荐全身燃脂
            
            scored_exercises.append((ex, score / 100))
            
        scored_exercises.sort(key=lambda x: x[1], reverse=True)
        return scored_exercises[:limit]

class DLSequenceEngine(RecommendationEngine):
    """深度学习序列推荐 (Transformer/RNN 模拟)"""
    def recommend(self, user, limit=5):
        # 获取用户过去 10 次训练的动作序列
        history = UserInteraction.objects.filter(user=user).order_by('timestamp')[:10]
        if history.count() < 3:
            return []
            
        # 模拟通过模型预测下一个最可能的动作
        # 在实际实现中，这里会调用一个加载好的 .pth 或 .h5 模型
        last_ex = history.last().exercise
        # 假设预测逻辑：通常练完一个部位会练互补部位
        complement_map = {
            'chest': 'back',
            'back': 'shoulders',
            'legs': 'abs',
            'shoulders': 'arms'
        }
        target = complement_map.get(last_ex.target_muscle, 'full_body')
        recs = Exercise.objects.filter(target_muscle=target)[:limit]
        return [(ex, 0.9) for ex in recs]

class RLAdaptiveEngine(RecommendationEngine):
    """强化学习动态引擎 (DQN/PPO 状态反馈)"""
    def recommend(self, user, limit=5):
        state, _ = UserState.objects.get_or_create(user=user)
        # 根据疲劳度调整
        if state.fatigue_level > 0.8:
            # 推荐低强度/恢复性动作
            recs = Exercise.objects.filter(difficulty='beginner')[:limit]
            return [(ex, 1.0) for ex in recs]
        
        # 模拟 探索(Exploration) vs 利用(Exploitation)
        if random.random() < 0.2: # 20% 几率探索新动作
            return [(ex, 0.7) for ex in Exercise.objects.order_by('?')[:limit]]
            
        # 否则利用过去表现最好的
        best_past = UserInteraction.objects.filter(user=user, interaction_type='finish').values('exercise').annotate(avg_score=Avg('score')).order_by('-avg_score')[:limit]
        return [(Exercise.objects.get(id=item['exercise']), item['avg_score']) for item in best_past]

class ColdStartEngine(RecommendationEngine):
    """冷启动推荐 (基于热门和专家规则)"""
    def recommend(self, user, limit=5):
        # 默认推荐站内最热门动作及符合其基础等级的基础动作
        popular = UserInteraction.objects.values('exercise').annotate(count=Count('id')).order_by('-count')[:limit]
        if popular:
            ids = [p['exercise'] for p in popular]
            return [(Exercise.objects.get(id=id), 0.8) for id in ids]
        
        # 兜底：推荐基础动作
        return [(ex, 0.5) for ex in Exercise.objects.all()[:limit]]

class HybridRecommender:
    """综合推荐调度器：根据用户状态和场景选择算法"""
    
    @staticmethod
    def get_recommendations(user, scenario='default'):
        # 1. 判断是否冷启动
        interaction_count = UserInteraction.objects.filter(user=user).count()
        if interaction_count < 5:
            engine = ColdStartEngine()
            algo_name = 'popularity'
        
        # 2. 根据场景选择
        elif scenario == 'discovery': # 发现新动作
            engine = ContentBasedEngine()
            algo_name = 'cosine'
        elif scenario == 'daily_plan': # 每日计划生成
            engine = MLEngine()
            algo_name = 'ml_regression'
        elif scenario == 'auto_adjust': # 实时训练调整
            engine = RLAdaptiveEngine()
            algo_name = 'rl_adaptive'
        else:
            # 默认使用 DL 序列预测
            engine = DLSequenceEngine()
            algo_name = 'dl_sequence'

        raw_recs = engine.recommend(user)
        
        # 3. 存储并持久化结果
        processed_recs = []
        RecommendedExercise.objects.filter(user=user, algorithm=algo_name).delete() # 清理旧推荐
        
        for rank, (ex, score) in enumerate(raw_recs, 1):
            rec_obj = RecommendedExercise.objects.create(
                user=user,
                exercise=ex,
                algorithm=algo_name,
                score=float(score),
                rank=rank,
                reason=f"基于 {algo_name} 算法为您定制"
            )
            processed_recs.append(rec_obj)
            
        return processed_recs
