from rest_framework import serializers
from .models import UserInteraction, RecommendedExercise, UserState
from exercises.serializers import ExerciseSerializer
from exercises.models import Exercise


class FeedbackActionSerializer(serializers.Serializer):
    action = serializers.CharField(required=True)

    def validate_action(self, value):
        normalized = str(value).strip().lower()
        allowed = {"like", "skip"}
        if normalized not in allowed:
            raise serializers.ValidationError("action must be one of: like, skip")
        return normalized


class ExerciseBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = ["id", "name", "target_muscle", "difficulty", "image_url", "demo_gif"]


class RecommendedExerciseSerializer(serializers.ModelSerializer):
    exercise = serializers.SerializerMethodField()

    def get_exercise(self, obj):
        # 默认返回轻量字段，前端可通过 brief=0 获取完整结构
        use_brief = self.context.get("brief", True)
        serializer_cls = ExerciseBriefSerializer if use_brief else ExerciseSerializer
        return serializer_cls(obj.exercise, context=self.context).data

    class Meta:
        model = RecommendedExercise
        fields = [
            "id",
            "exercise",
            "algorithm",
            "score",
            "rank",
            "reason",
            "is_seen",
            "created_at",
        ]


class UserInteractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserInteraction
        fields = "__all__"


class UserStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserState
        fields = "__all__"
