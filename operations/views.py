from typing import List, cast

from django.db import transaction
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from rest_framework import viewsets, status
from rest_framework.permissions import BasePermission, IsAdminUser, IsAuthenticated
from rest_framework.exceptions import ValidationError
from drf_spectacular.utils import extend_schema
from .models import Recommendation, Task
from .serializers import RecommendationSerializer, TaskSerializer, OperatorTaskUpdateSerializer
from common.audit import AuditLoggingMixin
from common.typing import RoleAwareUser
from users.permissions import IsAgronomistOrAdmin
from users.models import User


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

            # Создаём задачу только если переданы оба параметра
            if operator_id is not None and deadline:
                # Преобразуем operator_id в int, если это строка
                try:
                    operator_id = int(operator_id)
                except (ValueError, TypeError):
                    raise ValidationError(
                        {'operator_id': 'operator_id должен быть числом'},
                        code='invalid'
                    )

                # Валидируем и преобразуем deadline
                if isinstance(deadline, str):
                    parsed_deadline = parse_datetime(deadline)
                    if parsed_deadline is None:
                        raise ValidationError(
                            {'deadline': 'deadline должен быть в формате ISO 8601 (например: 2025-12-20T12:00:00Z)'},
                            code='invalid'
                        )
                    deadline = parsed_deadline

                # Проверяем, что пользователь существует
                try:
                    operator = User.objects.get(id=operator_id)
                except User.DoesNotExist:
                    raise ValidationError(
                        {'operator_id': f'Пользователь с ID {operator_id} не найден'},
                        code='not_found'
                    )

                # Проверяем, что у пользователя роль "Оператор"
                if not operator.role or operator.role.name != 'Оператор':
                    raise ValidationError(
                        {'operator_id': f'Пользователь с ID {operator_id} не является оператором'},
                        code='invalid_role'
                    )

                description = task_description or (
                    f'Выполнить план лечения по рекомендации #{recommendation.id} '
                    f'для диагноза #{recommendation.diagnosis_id}'
                )
                
                # Создаём задачу
                task = Task.objects.create(
                    recommendation=recommendation,
                    operator=operator,  # Используем объект User вместо operator_id
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
        # Если пользователь Оператор - используем урезанный сериализатор для чтения и обновления
        user = cast(RoleAwareUser, self.request.user)
        if user.role and user.role.name == 'Оператор':
            # Оператор использует ограниченный сериализатор для всех действий
            return OperatorTaskUpdateSerializer
        return TaskSerializer
    
    def perform_update(self, serializer: TaskSerializer) -> None:  # type: ignore[override]
        """
        Переопределяем обновление задачи для проверки статуса "Закрыта"
        """
        instance = serializer.instance
        if instance and instance.status == 'Закрыта':
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                {'status': 'Нельзя изменять задачу со статусом "Закрыта"'}
            )
        
        # Автоматически устанавливаем completed_at при статусе "Закрыта"
        if serializer.validated_data.get('status') == 'Закрыта':
            from django.utils import timezone
            serializer.validated_data['completed_at'] = timezone.now()
        
        self.update_and_log(serializer)

    def get_queryset(self) -> QuerySet[Task]:
        user = cast(RoleAwareUser, self.request.user)
        # Оператор видит только свои задачи
        if user.role and user.role.name == 'Оператор':
            return Task.objects.filter(operator=user).select_related('operator', 'recommendation')
        # Агрономы и Администраторы (включая is_staff) видят все задачи
        # Используем select_related для оптимизации запросов (избегаем N+1)
        queryset = Task.objects.all().select_related('operator', 'recommendation')
        # Сортируем по дате создания (новые сверху)
        return queryset.order_by('-created_at')

    def get_permissions(self) -> List[BasePermission]:
        if self.action in ['create', 'destroy']:
            return [IsAgronomistOrAdmin()]
        return super().get_permissions()