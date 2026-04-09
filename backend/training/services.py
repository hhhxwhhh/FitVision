import numpy as np
import random
from sklearn.metrics.pairwise import cosine_similarity
from django.db.models import Q
from users.models import UserProfile
from training.models import UserTrainingSession
from exercises.models import Exercise, ExerciseGraph
from utils.vector_db import VectorDB


class UserSimilarityService:
    @staticmethod
    def _resolve_goal(profile):
        """优先读取用户当前激活目标，避免直接依赖可能不存在的 profile.goal 字段。"""
        goal = getattr(profile, "goal", None)
        if goal:
            return goal

        try:
            active_goal = (
                profile.user.goals.filter(is_active=True)
                .order_by("-updated_at")
                .first()
            )
            if active_goal:
                # 统一到历史文案中使用的目标语义
                if active_goal.goal_type == "muscle_gain":
                    return "增肌"
                if active_goal.goal_type == "weight_loss":
                    return "减脂"
        except Exception:
            pass

        return "综合健身"

    @staticmethod
    def get_user_vector(profile):
        """将用户画像转化为向量 [BMI, 年龄, 水平, 目标_增肌...]"""
        if not profile:
            return np.zeros(6)

        # 简单归一化
        bmi = profile.weight / ((profile.height / 100) ** 2) if profile.height else 20
        norm_bmi = (bmi - 15) / 20
        norm_age = (profile.age - 15) / 45 if profile.age else 0.5
        norm_level = 1.0  # 默认

        # 目标 One-hot
        resolved_goal = UserSimilarityService._resolve_goal(profile)
        goal_vec = [0, 0, 0]
        if resolved_goal == "增肌":
            goal_vec[0] = 1
        elif resolved_goal == "减脂":
            goal_vec[1] = 1
        else:
            goal_vec[2] = 1

        return np.array([norm_bmi, norm_age, norm_level] + goal_vec)

    @staticmethod
    def recommend_for_cold_start(target_user):
        """寻找相似大神，直接 Copy 他的高分计划"""
        try:
            if not hasattr(target_user, "profile"):
                return None

            target_profile = target_user.profile
            target_vec = UserSimilarityService.get_user_vector(target_profile)

            other_profiles = UserProfile.objects.exclude(user=target_user).order_by(
                "-updated_at"
            )[:50]
            candidates = []

            for p in other_profiles:
                if p.gender != target_profile.gender:
                    continue

                p_vec = UserSimilarityService.get_user_vector(p)
                sim = cosine_similarity([target_vec], [p_vec])[0][0]
                if sim > 0.80:
                    candidates.append((p.user, sim))

            candidates.sort(key=lambda x: x[1], reverse=True)

            for user, sim in candidates[:3]:
                best_session = (
                    UserTrainingSession.objects.filter(
                        user=user, performance_score__gte=4.0
                    )
                    .order_by("-performance_score")
                    .first()
                )

                if best_session and best_session.plan:
                    return {
                        "source": "similarity",
                        "report_summary": f"为您找到与您体型相似度 {int(sim*100)}% 的伙伴正在使用的训练方案。",
                        "ref_session": best_session,
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
        if not exercise:
            return None
        if exercise.level <= user_level:
            return exercise

        prerequisites = exercise.prerequisites.all()
        if not prerequisites.exists():
            return exercise

        print(f"🛡️ 触发风控: {exercise.name}(Lv.{exercise.level}) -> 降级...")
        return SmartRecommendationService.get_safe_exercise(
            prerequisites.first(), user_level
        )

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
                if target_muscle in cand.target_muscle or target_muscle in str(
                    cand.category
                ):
                    seed_ex = cand
                    break

        if not seed_ex:
            seed_ex = Exercise.objects.filter(
                target_muscle__icontains=target_muscle
            ).first()

        if not seed_ex:
            return []

        safe_seed = SmartRecommendationService.get_safe_exercise(seed_ex, user_level)
        plan.append(safe_seed)
        used_ids.add(safe_seed.id)

        current = safe_seed
        while len(plan) < count:
            next_edges = ExerciseGraph.objects.filter(from_exercise=current).order_by(
                "-probability"
            )

            candidate = None
            if next_edges.exists() and random.random() < 0.7:
                candidate = next_edges.first().to_exercise
            else:
                candidate = (
                    Exercise.objects.filter(target_muscle=current.target_muscle)
                    .exclude(id__in=used_ids)
                    .order_by("?")
                    .first()
                )

            if candidate and candidate.id not in used_ids:
                safe_candidate = SmartRecommendationService.get_safe_exercise(
                    candidate, user_level
                )
                plan.append(safe_candidate)
                used_ids.add(safe_candidate.id)
                current = safe_candidate
            else:
                backup = Exercise.objects.exclude(id__in=used_ids).order_by("?").first()
                if backup:
                    plan.append(backup)
                    used_ids.add(backup.id)
                else:
                    break

        return plan
