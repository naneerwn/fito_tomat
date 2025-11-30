from typing import List, cast

from django.db import transaction
from django.db.models import QuerySet
from rest_framework import viewsets
from rest_framework.permissions import BasePermission, IsAdminUser, IsAuthenticated
from drf_spectacular.utils import extend_schema
from .models import Recommendation, Task
from .serializers import RecommendationSerializer, TaskSerializer, OperatorTaskUpdateSerializer
from common.audit import AuditLoggingMixin
from common.typing import RoleAwareUser
from users.permissions import IsAgronomistOrAdmin


@extend_schema(
    tags=['Операции'],
    description='Управление рекомендациями по лечению. Агрономы создают рекомендации на основе диагнозов, при создании можно автоматически создать задачу для оператора.'
)
class RecommendationViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    """
    ViewSet для управления рекомендациями по лечению.
    
    - GET /api/recommendations/ - получить список всех рекомендаций
    - GET /api/recommendations/{id}/ - получить информацию о конкретной рекомендации
    - POST /api/recommendations/ - создать новую рекомендацию (требуется роль Агроном или Администратор)
      При создании можно передать operator_id и deadline для автоматического создания задачи
    - PUT /api/recommendations/{id}/ - обновить рекомендацию (требуется роль Агроном или Администратор)
    - PATCH /api/recommendations/{id}/ - частично обновить рекомендацию (требуется роль Агроном или Администратор)
    - DELETE /api/recommendations/{id}/ - удалить рекомендацию (требуется роль Администратор)
    
    Права доступа:
    - Просмотр: все авторизованные пользователи
    - Создание/Изменение: Агрономы и Администраторы
    - Удаление: только Администраторы
    
    При создании рекомендации можно указать operator_id и deadline для автоматического создания задачи оператору.
    """
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


@extend_schema(
    tags=['Операции'],
    description='Управление задачами для операторов. Операторы могут обновлять статус своих задач, агрономы создают и управляют всеми задачами.'
)
class TaskViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    """
    ViewSet для управления задачами операторов.
    
    - GET /api/tasks/ - получить список задач (операторы видят только свои, агрономы и админы - все)
    - GET /api/tasks/{id}/ - получить информацию о конкретной задаче
    - POST /api/tasks/ - создать новую задачу (требуется роль Агроном или Администратор)
    - PUT /api/tasks/{id}/ - обновить задачу (операторы могут обновлять только статус)
    - PATCH /api/tasks/{id}/ - частично обновить задачу (операторы могут обновлять только статус)
    - DELETE /api/tasks/{id}/ - удалить задачу (требуется роль Агроном или Администратор)
    
    Права доступа:
    - Просмотр: все авторизованные пользователи (операторы видят только свои задачи)
    - Создание/Удаление: Агрономы и Администраторы
    - Обновление: операторы могут обновлять только статус своих задач, агрономы и админы - все поля
    
    Операторы используют ограниченный сериализатор, который позволяет изменять только статус задачи.
    """
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