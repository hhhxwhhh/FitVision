import os
import requests
import numpy as np
import random
from django.db.models import Q, Prefetch
from users.models import UserProfile, UserGoal
from training.models import UserTrainingSession
from exercises.models import Exercise, ExerciseGraph, UserExerciseRecord
from utils.vector_db import VectorDB  

class UserSimilarityService:
    @staticmethod
    def get_user_vector(profile):
        """将用户画像转化为向量 [BMI, 年龄, 水平, 目标_增肌...]"""
        if not profile: return np.zeros(6)
        
        # 简单归一化
        bmi = profile.weight / ((profile.height/100) ** 2) if profile.height else 20
        norm_bmi = (bmi - 15) / 20  
        norm_age = (profile.age - 15) / 45 if profile.age else 0.5
        norm_level = 1.0 # 默认
        
        # 目标 One-hot
        goal_vec = [0, 0, 0]
        if profile.goal == '增肌': goal_vec[0] = 1
        elif profile.goal == '减脂': goal_vec[1] = 1
        else: goal_vec[2] = 1
        
        return np.array([norm_bmi, norm_age, norm_level] + goal_vec)

    @staticmethod
    def recommend_for_cold_start(target_user):
        """寻找相似大神，直接 Copy 他的高分计划"""
        try:
            if not hasattr(target_user, 'userprofile'): return None
            
            target_profile = target_user.userprofile
            target_vec = UserSimilarityService.get_user_vector(target_profile)

            from sklearn.metrics.pairwise import cosine_similarity

            # 预取 user 与激活目标，避免循环里逐个查库。
            other_profiles = (
                UserProfile.objects.exclude(user=target_user)
                .select_related('user')
                .prefetch_related(
                    Prefetch(
                        'user__goals',
                        queryset=UserGoal.objects.filter(is_active=True),
                        to_attr='active_goals',
                    )
                )
                .order_by('-updated_at')[:50]
            )
            candidates = []
            
            for p in other_profiles:
                if p.gender != target_profile.gender: continue 
                
                p_vec = UserSimilarityService.get_user_vector(p)
                sim = cosine_similarity([target_vec], [p_vec])[0][0]
                if sim > 0.80: 
                    candidates.append((p.user, sim))
            
            candidates.sort(key=lambda x: x[1], reverse=True)

            # 一次性取出候选用户的高分会话，避免每个候选查一次。
            top_users = [user for user, _ in candidates[:3]]
            best_sessions = {}
            if top_users:
                sessions = (
                    UserTrainingSession.objects.filter(
                        user__in=top_users,
                        performance_score__gte=4.0,
                        plan__isnull=False,
                    )
                    .select_related('plan')
                    .order_by('-performance_score')
                )
                for session in sessions:
                    best_sessions.setdefault(session.user_id, session)

            for user, sim in candidates[:3]:
                best_session = best_sessions.get(user.id)
                
                if best_session and best_session.plan:
                    return {
                        "source": "similarity",
                        "report_summary": f"为您找到与您体型相似度 {int(sim*100)}% 的伙伴正在使用的训练方案。",
                        "ref_session": best_session
                    }
            return None
        except Exception as e:
            print(f"Similarity Service Error: {e}")
            return None

class SmartRecommendationService:
    
    @staticmethod
    def get_safe_exercise(exercise, user_level):
        """
        技能树降级逻辑：如果动作太难，递归找前置
        """
        if not exercise: return None
        if exercise.level <= user_level:
            return exercise

        prerequisites = exercise.prerequisites.all()
        if not prerequisites.exists():
            return exercise 
            
        print(f"触发风控: {exercise.name}(Lv.{exercise.level}) -> 降级...")
        return SmartRecommendationService.get_safe_exercise(prerequisites.first(), user_level)

    @staticmethod
    def generate_chain_plan(seed_query, user_level, target_muscle, count=4):

        plan = []
        used_ids = set()

        db = VectorDB()
        seed_ids = db.search(seed_query, top_k=10)
        
        seed_ex = None
        if seed_ids:
            candidates = Exercise.objects.filter(id__in=seed_ids)
            for cand in candidates:
                if target_muscle in cand.target_muscle or target_muscle in str(cand.category):
                    seed_ex = cand
                    break

        if not seed_ex:
            seed_ex = Exercise.objects.filter(target_muscle__icontains=target_muscle).first()

        if not seed_ex: return [] 

        safe_seed = SmartRecommendationService.get_safe_exercise(seed_ex, user_level)
        plan.append(safe_seed)
        used_ids.add(safe_seed.id)

        current = safe_seed
        while len(plan) < count:
            next_edges = ExerciseGraph.objects.filter(from_exercise=current).order_by('-probability')
            
            candidate = None
            if next_edges.exists() and random.random() < 0.7: 
                candidate = next_edges.first().to_exercise
            else:
                candidate = Exercise.objects.filter(
                    target_muscle=current.target_muscle
                ).exclude(id__in=used_ids).order_by('?').first()
            
            if candidate and candidate.id not in used_ids:
                safe_candidate = SmartRecommendationService.get_safe_exercise(candidate, user_level)
                plan.append(safe_candidate)
                used_ids.add(safe_candidate.id)
                current = safe_candidate
            else:
                backup = Exercise.objects.exclude(id__in=used_ids).order_by('?').first()
                if backup:
                    plan.append(backup)
                    used_ids.add(backup.id)
                else:
                    break
                
        return plan
    
    @staticmethod
    def verify_manual_selection(user, exercise_ids, pass_score=80.0):
        """严格校验用户手动选择的动作是否达标"""
        exercises = list(Exercise.objects.filter(id__in=exercise_ids))
        locked_reasons = []

        # 一次性拿到这批动作的前置关系与用户已通过的前置集合。
        prereq_pairs = Exercise.objects.filter(id__in=[ex.id for ex in exercises]).values_list(
            'id', 'prerequisites__id', 'prerequisites__name'
        )
        prereq_map: dict[int, list[tuple[int, str]]] = {}
        for exercise_id, prereq_id, prereq_name in prereq_pairs:
            if prereq_id is None:
                continue
            prereq_map.setdefault(exercise_id, []).append((prereq_id, prereq_name))

        passed_ids = set(
            UserExerciseRecord.objects.filter(
                user=user, accuracy_score__gte=pass_score
            ).values_list('exercise_id', flat=True)
        )

        name_map = {ex.id: ex.name for ex in exercises}
        for exercise_id, prereqs in prereq_map.items():
            for prereq_id, prereq_name in prereqs:
                if prereq_id in passed_ids:
                    continue
                locked_reasons.append(
                    f"【{name_map.get(exercise_id, '')}】未解锁："
                    f"需先以{pass_score}分完成前置【{prereq_name}】"
                )

        return len(locked_reasons) == 0, locked_reasons
    
    @staticmethod
    def evaluate_plan_difficulty(user, exercise_ids):
        """调用 AI 评估当前选择的动作组合难度"""

        exercises = Exercise.objects.filter(id__in=exercise_ids)
        ex_names = [ex.name for ex in exercises]
        
        # 提取用户的专属数据，让 AI 评估更精准
        try:
            profile = UserProfile.objects.get(user=user)
            user_info = f"身高: {profile.height}cm, 体重: {profile.weight}kg, 健身等级: {profile.fitness_level}"
        except UserProfile.DoesNotExist:
            user_info = "未知（新用户）"
            
        # 组装 Prompt
        prompt = f"""
        用户目前的身体数据是：{user_info}。
        用户计划在本次训练中进行以下动作组合：{', '.join(ex_names)}。
        请评估这个动作组合对该用户是否合理，并给出50字以内的简短建议（例如动作容量、体力分配提醒等）。直接返回文本，不要多余的寒暄。
        """

        try:
            api_key = os.environ.get("DEEPSEEK_API_KEY") 
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是一个严谨且专业的AI健身教练。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7, # 稍微降低温度，让回答更稳定专业
                "max_tokens": 150
            }

            response = requests.post(
                "https://api.deepseek.com/chat/completions", 
                json=payload, 
                headers=headers, 
                timeout=10 
            )
            response.raise_for_status() # 如果返回 4xx 或 5xx 状态码，直接抛出异常
            
            # 解析大模型返回的数据
            result = response.json()
            ai_advice = result['choices'][0]['message']['content'].strip()
            
        except requests.exceptions.RequestException as e:
            print(f"DeepSeek 网络请求失败: {e}")
            ai_advice = "网络开小差了，请根据自身状态合理安排训练节奏哦！"
        except KeyError as e:
            print(f"DeepSeek 返回数据解析异常: {e}")
            ai_advice = "AI 评估暂时不可用，请注意控制各动作的组间休息。"
        except Exception as e:
            print(f"未知 AI 评估错误: {e}")
            ai_advice = "系统繁忙，请量力而行，注意安全。"
            
        return ai_advice