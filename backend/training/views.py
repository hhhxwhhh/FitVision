from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from .services import SmartRecommendationService 
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
import json 
from openai import OpenAI  
from utils.vector_db import VectorDB
import os
from .services import UserSimilarityService, SmartRecommendationService

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

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

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
    
    exercise_ids = request.data.get('exercise_ids', []) 

    try:
        plan = None
        plan_day = None
        
        if plan_id:
            plan = get_object_or_404(TrainingPlan, id=plan_id, is_active=True)
            
        if plan_day_id:
            plan_day = get_object_or_404(TrainingPlanDay, id=plan_day_id)
            if not plan:
                plan = plan_day.plan

        session = UserTrainingSession.objects.create(
            user=user,
            plan=plan,
            plan_day=plan_day,
            start_time=timezone.now(),
            total_exercises=plan_day.exercises.count() if plan_day else len(exercise_ids)
        )

        records_to_create = []

        # 场景 A: 走传统的静态模板路线
        if plan_day:
            plan_exercises = TrainingPlanExercise.objects.filter(training_day=plan_day).order_by('order')
            for pe in plan_exercises:
                records_to_create.append(
                    UserTrainingExerciseRecord(
                        session=session,
                        plan_exercise=pe,
                        exercise=pe.exercise,
                        sets_completed=0,  
                        form_score=0.0   
                    )
                )
                
        # 场景 B: 走 AI 推荐的动态散装动作路线
        elif exercise_ids:
            exercises = Exercise.objects.filter(id__in=exercise_ids)
            ex_dict = {ex.id: ex for ex in exercises}
            for ex_id in exercise_ids:
                if ex_id in ex_dict:
                    records_to_create.append(
                        UserTrainingExerciseRecord(
                            session=session,
                            exercise=ex_dict[ex_id],
                            sets_completed=0,
                            form_score=0.0
                        )
                    )

        if records_to_create:
            UserTrainingExerciseRecord.objects.bulk_create(records_to_create)

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
    
    try:
        # 假设 session 关联了 exercise_records
        records = session.exercise_records.order_by('created_at') # 确保按时间排序
        exercises = [r.exercise for r in records]
        
        # 更新 A -> B 的权重
        for i in range(len(exercises) - 1):
            curr = exercises[i]
            next_ex = exercises[i+1]
            
            # 找到或创建边
            edge, _ = ExerciseGraph.objects.get_or_create(
                from_exercise=curr, 
                to_exercise=next_ex
            )
            
            # 加权逻辑：完成度越高权重越大
            weight_add = 1
            if session.performance_score >= 4: weight_add = 2
            
            edge.weight += weight_add
            edge.save()
            
            # (可选) 重新计算概率: probability = weight / sum(all_weights)
            # 建议放到 Celery 异步任务里，或者每隔一段时间批量算
            
    except Exception as e:
        print(f"Graph Update Error: {e}")

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
            temperature=1.2,
            timeout=60.0
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
        "level_str": request.data.get('level', '初学者'),
        "days": int(request.data.get('days', 3)), # 🔥 确保转为 int
        "focus": request.data.get('focus', '全身'), 
        "equipment": request.data.get('equipment', '哑铃')
    }
    
    # 等级映射
    level_map = {'初学者': 1, '中级': 3, '高级': 5}
    user_level = level_map.get(config['level_str'], 1)
    
    # 映射部位到英文
    muscle_map = {
        '胸': 'chest', '背': 'back', '腿': 'legs', '肩': 'shoulders', '手': 'arms', '腹': 'abs',
        '全身': 'full_body'
    }
    main_target_muscle = 'full_body'
    for k, v in muscle_map.items():
        if k in config['focus']:
            main_target_muscle = v
            break

    # ==========================================
    # 策略 A: 冷启动 (相似用户推荐)
    # ==========================================
    # 只有训练记录极少时才触发
    if UserTrainingSession.objects.filter(user=user).count() < 3:
        print("🔍 触发冷启动推荐...")
        cold_start_result = UserSimilarityService.recommend_for_cold_start(user)
        
        if cold_start_result:
            ref_session = cold_start_result['ref_session']
            exercises_data = []
            
            # 获取大神的历史记录
            from .models import UserTrainingExerciseRecord
            records = UserTrainingExerciseRecord.objects.filter(session=ref_session).order_by('created_at')
            
            for rec in records:
                ex = rec.exercise
                exercises_data.append({
                    "id": ex.id,
                    "name": ex.name,
                    "target_muscle": ex.target_muscle,
                    "sets": rec.sets_completed or 3,
                    "reps": "8-12次",
                    "gif": ex.demo_gif.url if ex.demo_gif else "",
                    "img": ex.image_url if hasattr(ex, 'image_url') else "",
                    "ai_desc": f"大神同款：{cold_start_result.get('report_summary', '经典训练')}"
                })
            
            if exercises_data:
                # 冷启动我们暂时只给一天体验版，或者你可以简单复制几天
                return Response({
                    "report_title": "新手专属 · 达人推荐",
                    "report_summary": "为您匹配到了体型相似的健身达人推荐计划，快速上手！",
                    "weekly_schedule": [{
                        "day": "Day 1",
                        "title": "达人验证 · 核心训练",
                        "type": "training",
                        "status": "难度适中",
                        "exercises": exercises_data
                    }],
                    "suggestions": ["这是根据和你体型相似的用户生成的验证方案"],
                    "goal_progress": 0
                })

    # ==========================================
    # 策略 B: 智能生成 (M3E + Graph + SkillTree)
    # ==========================================
    print(f"🧠 智能生成启动: {config['focus']} (Lv.{user_level}) - {config['days']}天")
    
    weekly_schedule = []

    # 🔥 定义分化训练逻辑 (如果选全身，自动每天换部位)
    split_routine = [
        {'query': '胸肌训练', 'muscle': 'chest', 'title': '推力强化 (胸部)'},
        {'query': '背部训练', 'muscle': 'back',  'title': '背部刻画 (拉力)'},
        {'query': '腿部训练', 'muscle': 'legs',  'title': '下肢力量 (腿部)'},
        {'query': '肩部训练', 'muscle': 'shoulders', 'title': '肩部塑形'},
        {'query': '手臂训练', 'muscle': 'arms',  'title': '手臂轰炸'},
        {'query': '腹肌训练', 'muscle': 'abs',   'title': '核心强化'},
    ]

    # 🔥 循环生成每一天的计划
    for day_i in range(config['days']):
        
        # 1. 决定今天的训练重点
        if main_target_muscle == 'full_body':
            # 如果是练全身，就轮询 split_routine
            routine = split_routine[day_i % len(split_routine)]
            daily_query = routine['query']
            daily_muscle = routine['muscle']
            daily_title = routine['title']
        else:
            # 如果是专项（比如只练胸），就一直练胸，但标题变一下
            daily_query = config['focus']
            daily_muscle = main_target_muscle
            daily_title = f"{config['focus']}专项 (Day {day_i + 1})"

        # 2. 调用 Service 生成当天的动作链
        exercise_chain = SmartRecommendationService.generate_chain_plan(
            seed_query=daily_query, 
            user_level=user_level,
            target_muscle=daily_muscle,
            count=4 
        )
        
        # 3. 格式化动作数据
        exercises_data = []
        for ex in exercise_chain:
            exercises_data.append({
                "id": ex.id,
                "name": ex.name,
                "search_query": ex.name,
                "target_muscle": ex.target_muscle,
                "sets": 3,
                "reps": "8-12次",
                "gif": ex.demo_gif.url if ex.demo_gif else "",
                "img": ex.image_url if hasattr(ex, 'image_url') else "",
                "ai_desc": f"适合Lv.{user_level}的进阶动作"
            })
        
        # 4. 加入周计划列表
        weekly_schedule.append({
            "day": f"Day {day_i + 1}", # 显示第几天
            "title": daily_title,
            "type": "training",
            "status": "预计消耗 250kcal",
            "exercises": exercises_data
        })

    # 5. 返回结果
    final_response = {
        "report_title": "FitVision 智能进化计划",
        "report_summary": f"已为您生成 {config['days']} 天的{config['focus']}进阶方案。动作编排符合运动生物力学，兼顾了安全与效率。",
        "weekly_schedule": weekly_schedule,
        "suggestions": ["注意顶峰收缩", "离心过程控制在2秒", "组间休息60-90秒"],
        "goal_progress": 0
    }

    return Response(final_response)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pre_workout_analysis(request):
    """训练前：校验锁定状态"""
    user = request.user
    # 假设前端传过来的是动作 ID 数组，例如 {"exercise_ids": [1, 5, 8]}
    exercise_ids = request.data.get('exercise_ids', [])
    
    if not exercise_ids:
        return Response({"error": "请提供动作ID"}, status=400)

    # 1. 硬校验：查锁
    is_allowed, reasons = SmartRecommendationService.verify_manual_selection(user, exercise_ids)
    
    if not is_allowed:
        return Response({
            "status": "locked",
            "message": "存在未解锁的动作",
            "reasons": reasons
        }, status=403)
        
    # 2. 软校验：调用 AI 评估计划难度 (补上这段代码！)
    ai_advice = SmartRecommendationService.evaluate_plan_difficulty(user, exercise_ids)
    
    return Response({
        "status": "success",
        "message": "动作均已解锁，可以开始训练！",
        "ai_advice": ai_advice  # 把大模型的建议传给前端 Vue
    }, status=200)