from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from .models import Recommendation, Task
from .serializers import RecommendationSerializer, TaskSerializer, OperatorTaskUpdateSerializer
from common.audit import AuditLoggingMixin
from users.permissions import IsAgronomistOrAdmin


class RecommendationViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = Recommendation.objects.all()
    serializer_class = RecommendationSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        # Если действие - удаление
        if self.action == 'destroy':
            # Разрешаем удаление только Админу/Суперпользователю
            return [IsAdminUser()]
        if self.action in ['create', 'update', 'partial_update']:
            return [IsAgronomistOrAdmin()]
        return super().get_permissions()


class TaskViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = Task.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        # Если пользователь Оператор и пытается обновить задачу - используем урезанный сериализатор
        user = self.request.user
        if self.action in ['update', 'partial_update'] and user.role and user.role.name == 'Оператор':
            return OperatorTaskUpdateSerializer
        return TaskSerializer

    def get_queryset(self):
        user = self.request.user
        # Оператор видит свои задачи, Агроном - все
        if user.role and user.role.name == 'Оператор':
            return Task.objects.filter(operator=user)
        return Task.objects.all()

    def get_permissions(self):
        if self.action in ['create', 'destroy']:
            return [IsAgronomistOrAdmin()]
        return super().get_permissions()