from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
import json 
from openai import OpenAI  
from utils.vector_db import VectorDB

from .models import TrainingPlan, TrainingPlanDay, TrainingPlanExercise, UserTrainingSession, UserTrainingExerciseRecord
from .serializers import (
    TrainingPlanSerializer,
    TrainingPlanDetailSerializer,
    TrainingPlanDaySerializer,
    UserTrainingSessionSerializer,
    UserTrainingSessionDetailSerializer,
    UserTrainingExerciseRecordSerializer
)
from exercises.models import Exercise
from users.models import UserProfile

DEEPSEEK_API_KEY = "sk-2b8ed8fe048b4ceeb9118a1e150b9ea6"

class TrainingPlanListView(generics.ListAPIView):
    """获取所有公开的训练计划，支持过滤、搜索和排序"""
    queryset = TrainingPlan.objects.filter(is_active=True, is_public=True)
    serializer_class = TrainingPlanSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['goal', 'difficulty', 'category']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'difficulty', 'duration_weeks', 'created_at']
    ordering = ['-created_at']


class TrainingPlanDetailView(generics.RetrieveAPIView):
    """获取训练计划详情"""
    queryset = TrainingPlan.objects.filter(is_active=True)
    serializer_class = TrainingPlanDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_training_session(request):
    """开始一个新的训练会话"""
    user = request.user
    plan_id = request.data.get('plan_id')
    plan_day_id = request.data.get('plan_day_id')
    
    try:
        plan = None
        plan_day = None
        
        if plan_id:
            plan = get_object_or_404(TrainingPlan, id=plan_id, is_active=True)
            
        if plan_day_id:
            plan_day = get_object_or_404(TrainingPlanDay, id=plan_day_id)
            
            # 如果提供了plan_day但没有提供plan，则从plan_day获取plan
            if not plan:
                plan = plan_day.plan
                
        # 创建训练会话
        session = UserTrainingSession.objects.create(
            user=user,
            plan=plan,
            plan_day=plan_day,
            start_time=timezone.now(),
            total_exercises=plan_day.exercises.count() if plan_day else 0
        )
        
        serializer = UserTrainingSessionSerializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def complete_training_session(request, session_id):
    """完成训练会话（AI 判官版）"""
    user = request.user
    session = get_object_or_404(UserTrainingSession, id=session_id, user=user)
    
    if session.is_completed:
        return Response({'error': '训练会话已结束'}, status=status.HTTP_400_BAD_REQUEST)

    # 1. 获取基本数据
    session.end_time = timezone.now() if not request.data.get('end_time') else request.data.get('end_time')
    session.is_completed = True
    session.completed_exercises = request.data.get('completed_exercises', session.total_exercises)
    session.calories_burned = request.data.get('calories_burned', 0)
    
    # 获取用户的自评数据
    user_self_rating = request.data.get('performance_score', 0) 
    user_feedback = request.data.get('user_feedback', '')

    # 计算时长
    duration_seconds = 0
    if session.end_time and session.start_time:
        duration_seconds = (session.end_time - session.start_time).total_seconds()

    # 2. 🔥 呼叫 AI 判官
    # 注意：这里调用的是下面定义的辅助函数，不需要 self
    ai_result = call_deepseek_ai(session, duration_seconds, user_self_rating, user_feedback)
    
    # 3. 🔥 应用 AI 的裁决
    # 如果 AI 返回了分数，就用 AI 的；否则用用户的兜底
    final_score = ai_result.get('score', user_self_rating)
    
    session.performance_score = final_score
    session.ai_analysis = ai_result.get('analysis', 'AI 正在分析...')
    session.ai_tags = ai_result.get('tags', [])

    session.save()

    # 4. 记录日志 (TrainingLog)
    try:
        from users.models import TrainingLog
        TrainingLog.objects.create(
            user=user,
            action_name=f"训练计划: {session.plan.name if session.plan else '自定义训练'}",
            count=session.completed_exercises,
            duration=duration_seconds,
            accuracy_score=session.performance_score, # 这里存的是 AI 修正后的分数
            calories=session.calories_burned
        )
    except Exception as e:
        print(f"TrainingLog Error: {e}")

    serializer = UserTrainingSessionSerializer(session)

    response_data = serializer.data
    response_data['ai_report'] = {
        "aiAnalysis": session.ai_analysis,
        "tags": session.ai_tags,
        "score": session.performance_score # 返回给前端显示
    }
    
    return Response(response_data, status=status.HTTP_200_OK)


class UserTrainingSessionListView(generics.ListAPIView):
    """获取用户的训练会话记录"""
    serializer_class = UserTrainingSessionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return UserTrainingSession.objects.filter(user=self.request.user).order_by('-start_time')


class UserTrainingSessionDetailView(generics.RetrieveAPIView):
    """获取用户训练会话详情"""
    serializer_class = UserTrainingSessionDetailSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return UserTrainingSession.objects.filter(user=self.request.user)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def record_training_exercise(request):
    """记录用户训练中的动作完成情况"""
    user = request.user
    session_id = request.data.get('session_id')
    
    session = get_object_or_404(UserTrainingSession, id=session_id, user=user)
    
    if session.is_completed:
        return Response({'error': '训练会话已结束，无法添加记录'}, status=status.HTTP_400_BAD_REQUEST)
    
    # 创建训练动作记录
    record_data = request.data.copy()
    record_data.pop('session', None)
    
    serializer = UserTrainingExerciseRecordSerializer(data=record_data)
    if serializer.is_valid():
        record = serializer.save(session=session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_training_exercise_record(request, record_id):
    """删除训练动作记录"""
    user = request.user
    record = get_object_or_404(UserTrainingExerciseRecord, id=record_id, session__user=user)
    
    # 检查会话是否已完成
    if record.session.is_completed:
        return Response({'error': '训练会话已结束，无法删除记录'}, status=status.HTTP_400_BAD_REQUEST)
    
    record.delete()
    return Response({'message': '删除成功'}, status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_training_stats(request):
    """获取用户训练统计数据"""
    user = request.user
    
    try:
        profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        profile = None
    
    # 统计用户的训练数据
    total_sessions = UserTrainingSession.objects.filter(user=user, is_completed=True).count()
    
    # 计算总训练时长
    sessions_with_duration = UserTrainingSession.objects.filter(
        user=user, 
        is_completed=True
    ).exclude(end_time=None).exclude(start_time=None)
    
    total_duration = 0
    for session in sessions_with_duration:
        total_duration += (session.end_time - session.start_time).total_seconds()
    
    total_calories = UserTrainingSession.objects.filter(user=user, is_completed=True).aggregate(
        Sum('calories_burned')
    )['calories_burned__sum'] or 0
    
    best_record = UserTrainingSession.objects.filter(user=user, is_completed=True).order_by('-performance_score').first()
    
    # 最近7天的训练次数
    week_ago = timezone.now() - timedelta(days=7)
    weekly_sessions = UserTrainingSession.objects.filter(
        user=user, 
        is_completed=True, 
        start_time__gte=week_ago
    ).count()
    
    stats = {
        'profile_info': {
            'nickname': profile.nickname if profile else '',
            'gender': profile.gender if profile else '',
            'age': profile.age if profile else 0,
            'height': profile.height if profile else 0,
            'weight': profile.weight if profile else 0,
            'fitness_level': profile.fitness_level if profile else '',
        } if profile else None,
        'total_sessions': total_sessions,
        'total_duration': int(total_duration),  # 转换为整数秒
        'total_duration_formatted': str(timedelta(seconds=int(total_duration))),  # 格式化时间
        'weekly_sessions': weekly_sessions,
        'total_calories': round(total_calories, 2),
        'best_performance_score': best_record.performance_score if best_record else 0,
        'favorite_plan': best_record.plan.name if best_record and best_record.plan else '',
    }
    
    return Response(stats, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_plan_days(request, plan_id):
    """获取指定训练计划的所有天数安排"""
    user = request.user
    plan = get_object_or_404(TrainingPlan, id=plan_id, is_active=True)
    
    # 如果计划不是公开的，检查是否是创建者
    if not plan.is_public and plan.created_by != user:
        return Response({'error': '无权访问此训练计划'}, status=status.HTTP_403_FORBIDDEN)
    
    days = TrainingPlanDay.objects.filter(plan=plan).order_by('day_number')
    serializer = TrainingPlanDaySerializer(days, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

def call_deepseek_ai(session, duration_seconds, user_rating, user_feedback):
    """
    辅助函数：让 AI 决定分数
    注意：这是一个独立函数，不需要 'self' 参数
    """
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    duration_minutes = round(duration_seconds / 60, 1)

    # 🔥 修改 Prompt：让 AI 当判官
    # 注意：这里用了 session.calories_burned 而不是 session.calories
    prompt = f"""
    你是一位严格但幽默的健身教练。用户完成了一次训练，数据如下：
    - 动作数量：{session.completed_exercises}个
    - 消耗热量：{session.calories_burned}千卡
    - 训练时长：{duration_minutes}分钟
    - 【用户自评】：{user_rating}/5分
    - 【用户主观反馈】：{user_feedback}
    
    请根据客观训练数据（动作数、热量）和用户的主观感受，生成一份分析报告，并给出一个【最终综合评分】。
    
    评分逻辑：
    1. 如果动作数量很少（<3个）或热量很低，即使如同用户自评满分，最终评分也不能超过 2.0 分（可以幽默地吐槽）。
    2. 如果数据扎实，且用户感觉良好，可以给高分。
    
    要求返回纯 JSON：
    {{
        "score": (数字, 0-5之间, 保留1位小数),
        "analysis": (字符串, 150字以内, 包含HTML标签如<b>),
        "tags": (字符串数组, 3个短标签)
    }}
    """

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个输出 JSON 格式的健身教练助手。"},
                {"role": "user", "content": prompt},
            ],
            response_format={ 'type': 'json_object' },
            temperature=1.2 
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"DeepSeek Error: {e}")
        # 出错时的兜底
        return {
            "score": user_rating, 
            "analysis": "AI 暂时掉线了，但你的努力已被记录。", 
            "tags": ["训练完成"]
        }

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_smart_plan(request):
    user = request.user
    
    # 1. 接收配置
    config = {
        "goal": request.data.get('goal', '增肌'),
        "level": request.data.get('level', '初学者'),
        "days": request.data.get('days', 3),
        "duration": request.data.get('duration', 45),
        "focus": request.data.get('focus', '全身'),
        "equipment": request.data.get('equipment', '哑铃')
    }

    # 2. 构造 Prompt：增加 target_muscle 约束
    prompt = f"""
    你是一位健身专家。请为用户生成一周训练计划。
    
    用户档案：目标{config['goal']}，{config['days']}天/周，重点{config['focus']}，器材{config['equipment']}。

    请严格返回 JSON。对于每个动作，必须包含两个关键字段：
    1. "search_query": 准确的动作中文描述。
    2. "target_muscle": 必须从以下单词中选一个最匹配的：['chest', 'back', 'shoulders', 'arms', 'abs', 'legs', 'glutes', 'full_body']

    JSON 格式示例：
    {{
        "report_title": "AI定制计划",
        "report_summary": "HTML分析...",
        "weekly_schedule": [
            {{
                "day": "周一", 
                "title": "胸肌训练", 
                "type": "training",
                "status": "消耗300kcal",
                "exercises": [
                    {{
                        "search_query": "哑铃平板卧推", 
                        "target_muscle": "chest", 
                        "sets": 4,
                        "reps": "12次"
                    }}
                ]
            }},
            ... (生成 {config['days']} 个训练日)
        ],
        "suggestions": [], 
        "goal_progress": 0
    }}
    """

    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

    try:
        # 3. 呼叫 AI (只呼叫一次！)
        print("🤖 AI 正在生成计划结构...")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个输出纯 JSON 的健身专家。"},
                {"role": "user", "content": prompt},
            ],
            response_format={ 'type': 'json_object' },
            temperature=1.1
        )
        ai_plan = json.loads(response.choices[0].message.content)

        # 4. 🔥 向量召回 + 逻辑强校验
        db = VectorDB()
        print("🔍 开始三级匹配...")

        for day in ai_plan.get('weekly_schedule', []):
            if day.get('type') != 'training':
                continue
                
            real_exercises = []
            # 🔥 新增：记录今天已经选过的动作 ID (去重集合)
            used_exercise_ids = set()
            
            for ex_item in day.get('exercises', []):
                query = ex_item.get('search_query', '')
                required_muscle = ex_item.get('target_muscle', '').lower()
                
                final_match = None
                
                # -------------------------------------------------
                # 1. 向量检索 (扩大搜 Top 10，给备选留足空间)
                # -------------------------------------------------
                candidate_ids = db.search(query, top_k=10)
                
                if candidate_ids:
                    candidates = Exercise.objects.filter(id__in=candidate_ids)
                    
                    # 筛选出部位匹配的候选人
                    valid_candidates = [c for c in candidates if c.target_muscle == required_muscle]
                    
                    # 🔥 核心去重逻辑：
                    # 在符合部位的动作里，找一个【还没被选过】的
                    for cand in valid_candidates:
                        if cand.id not in used_exercise_ids:
                            final_match = cand
                            break # 找到了！跳出循环
                    
                    # ⚠️ 如果所有候选人都用过了（动作库太小），没办法，只能复用第一个
                    if not final_match and valid_candidates:
                        final_match = valid_candidates[0]
                        # 可以在这里打印个日志提醒自己
                        print(f"⚠️ 动作库不足，被迫重复使用: {final_match.name}")

                # -------------------------------------------------
                # 2. 关键词兜底 (如果向量没搜到)
                # -------------------------------------------------
                if not final_match:
                    keywords = query.replace("哑铃", "").replace("杠铃", "").replace("动作", "").strip()
                    if len(keywords) > 1:
                        # 尝试去数据库捞一个没用过的、名字相似的、部位对的
                        backup_qs = Exercise.objects.filter(
                            name__icontains=keywords[:2],
                            target_muscle=required_muscle
                        )
                        for backup in backup_qs:
                            if backup.id not in used_exercise_ids:
                                final_match = backup
                                break
                        
                        # 如果还没找到，就随便拿第一个
                        if not final_match:
                            final_match = backup_qs.first()

                # -------------------------------------------------
                # 3. 组装数据
                # -------------------------------------------------
                if final_match:
                    # 📝 登记到“已用”名单，下次不许再选它
                    used_exercise_ids.add(final_match.id)
                    
                    real_exercises.append({
                        "id": final_match.id,
                        "name": final_match.name,
                        "gif": final_match.demo_gif.url if final_match.demo_gif else "",
                        "img": final_match.image_url,
                        "sets": ex_item.get('sets', 3),
                        "reps": ex_item.get('reps', '10次'),
                        "ai_desc": query,
                        "is_real": True
                    })
                else:
                    # 彻底失败，纯文本展示
                    real_exercises.append({
                        "id": 0,
                        "name": ex_item.get('search_query'),
                        "gif": "",
                        "img": "",
                        "sets": ex_item.get('sets', 3),
                        "reps": ex_item.get('reps', '10次'),
                        "ai_desc": query,
                        "is_real": False
                    })
            
            day['exercises'] = real_exercises

        return Response(ai_plan)
    except json.JSONDecodeError:
        print("DeepSeek 返回的不是有效 JSON")
        return Response({"error": "AI 脑子瓦特了，返回格式错误，请重试"}, status=500)
    except Exception as e:
        import traceback
        traceback.print_exc() # 打印详细报错堆栈到终端，方便调试
        print(f"Plan Generation Error: {e}")
        return Response({"error": f"生成失败: {str(e)}"}, status=500)