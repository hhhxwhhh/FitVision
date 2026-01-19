from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Avg, Max
from .models import UserDailyStats, UserBodyMetric, ExerciseProgress
from .serializers import UserDailyStatsSerializer, UserBodyMetricSerializer, ExerciseProgressSerializer
from datetime import datetime, timedelta

class UserDailyStatsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = UserDailyStats.objects.all()
    serializer_class = UserDailyStatsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        days = int(request.query_params.get('days', 7))
        start_date = datetime.now().date() - timedelta(days=days)
        
        stats = self.get_queryset().filter(date__gte=start_date)
        
        data = {
            "total_calories": stats.aggregate(Sum('total_calories_burned'))['total_calories_burned__sum'] or 0,
            "total_duration": stats.aggregate(Sum('total_duration_minutes'))['total_duration_minutes__sum'] or 0,
            "avg_form_score": stats.aggregate(Avg('average_form_score'))['average_form_score__avg'] or 0,
            "daily_breakdown": UserDailyStatsSerializer(stats, many=True).data
        }
        return Response(data)

class UserBodyMetricViewSet(viewsets.ModelViewSet):
    queryset = UserBodyMetric.objects.all()
    serializer_class = UserBodyMetricSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ExerciseProgressViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ExerciseProgress.objects.all()
    serializer_class = ExerciseProgressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    @action(detail=False, methods=['get'], url_path='by-exercise/(?P<exercise_id>[^/.]+)')
    def by_exercise(self, request, exercise_id=None):
        progress = self.get_queryset().filter(exercise_id=exercise_id).order_by('date')
        serializer = self.get_serializer(progress, many=True)
        return Response(serializer.data)
