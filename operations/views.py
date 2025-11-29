from typing import List, cast

from django.db import transaction
from django.db.models import QuerySet
from rest_framework import viewsets
from rest_framework.permissions import BasePermission, IsAdminUser, IsAuthenticated
from .models import Recommendation, Task
from .serializers import RecommendationSerializer, TaskSerializer, OperatorTaskUpdateSerializer
from common.audit import AuditLoggingMixin
from common.typing import RoleAwareUser
from users.permissions import IsAgronomistOrAdmin


class RecommendationViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = Recommendation.objects.all()
    serializer_class = RecommendationSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self) -> List[BasePermission]:
        # Если действие - удаление
        if self.action == 'destroy':
            # Разрешаем удаление только Админу/Суперпользователю
            return [IsAdminUser()]
        if self.action in ['create', 'update', 'partial_update']:
            return [IsAgronomistOrAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer: RecommendationSerializer) -> None:  # type: ignore[override]
        """
        При создании рекомендации автоматически создаём связанную задачу для оператора,
        если переданы operator_id и deadline.

        Это реализует сценарий из ТЗ: после подтверждения диагноза и создания
        рекомендации оператор получает задачу на выполнение плана лечения.
        """
        request = self.request
        operator_id = request.data.get('operator_id')
        deadline = request.data.get('deadline')
        task_description = request.data.get('task_description') or ''

        with transaction.atomic():
            # Агроном берётся из текущего пользователя
            recommendation = self.save_and_log_create(serializer, agronomist=request.user)

            if operator_id and deadline:
                description = task_description or (
                    f'Выполнить план лечения по рекомендации #{recommendation.id} '
                    f'для диагноза #{recommendation.diagnosis_id}'
                )
                Task.objects.create(
                    recommendation=recommendation,
                    operator_id=operator_id,
                    description=description,
                    status='Назначена',
                    deadline=deadline,
                )


class TaskViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = Task.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        # Если пользователь Оператор и пытается обновить задачу - используем урезанный сериализатор
        user = cast(RoleAwareUser, self.request.user)
        if self.action in ['update', 'partial_update'] and user.role and user.role.name == 'Оператор':
            return OperatorTaskUpdateSerializer
        return TaskSerializer

    def get_queryset(self) -> QuerySet[Task]:
        user = cast(RoleAwareUser, self.request.user)
        # Оператор видит свои задачи, Агроном - все
        if user.role and user.role.name == 'Оператор':
            return Task.objects.filter(operator=user)
        return Task.objects.all()

    def get_permissions(self) -> List[BasePermission]:
        if self.action in ['create', 'destroy']:
            return [IsAgronomistOrAdmin()]
        return super().get_permissions()