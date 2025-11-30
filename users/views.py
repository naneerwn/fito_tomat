from typing import List, cast

from django.db.models import QuerySet
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission, IsAdminUser, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from .models import Role, User
from .serializers import RoleSerializer, UserSerializer
from common.audit import AuditLoggingMixin
from common.typing import RoleAwareUser


@extend_schema(
    tags=['Пользователи и роли'],
    description='Управление ролями пользователей системы. Доступно только администраторам.'
)
class RoleViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    """
    ViewSet для управления ролями пользователей.
    
    - GET /api/roles/ - получить список всех ролей (требуется роль Администратор)
    - GET /api/roles/{id}/ - получить информацию о конкретной роли (требуется роль Администратор)
    - POST /api/roles/ - создать новую роль (требуется роль Администратор)
    - PUT /api/roles/{id}/ - обновить роль (требуется роль Администратор)
    - PATCH /api/roles/{id}/ - частично обновить роль (требуется роль Администратор)
    - DELETE /api/roles/{id}/ - удалить роль (требуется роль Администратор)
    
    Доступ: только администраторы системы.
    """
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAdminUser] # Только админ управляет ролями

@extend_schema(
    tags=['Пользователи и роли'],
    description='Управление пользователями системы. Обычные пользователи могут просматривать только свою информацию, администраторы - всех пользователей.'
)
class UserViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    """
    ViewSet для управления пользователями системы.
    
    - GET /api/users/ - получить список пользователей (обычные пользователи видят только себя, админы - всех)
    - GET /api/users/{id}/ - получить информацию о пользователе
    - GET /api/users/me/ - получить информацию о текущем авторизованном пользователе
    - POST /api/users/ - создать нового пользователя (требуется роль Администратор)
    - PUT /api/users/{id}/ - обновить пользователя (требуется роль Администратор)
    - PATCH /api/users/{id}/ - частично обновить пользователя (требуется роль Администратор)
    - DELETE /api/users/{id}/ - удалить пользователя (требуется роль Администратор)
    
    Права доступа:
    - Просмотр: все авторизованные пользователи (видят только свою информацию, кроме админов)
    - Создание/Изменение/Удаление: только администраторы
    """
    queryset = User.objects.all().order_by('id')
    serializer_class = UserSerializer

    def get_permissions(self) -> List[BasePermission]:
        # Удаление пользователей - только админ
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_queryset(self) -> QuerySet[User]:
        user = cast(RoleAwareUser, self.request.user)
        # Админ видит всех, остальные - только себя (специфика безопасности)
        if user.is_staff or (user.role and user.role.name == 'Администратор'):
            return self.queryset
        return self.queryset.filter(id=user.id)

    @extend_schema(
        summary='Получить текущего пользователя',
        description='Возвращает информацию о текущем авторизованном пользователе',
        tags=['Пользователи и роли']
    )
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request: Request) -> Response:
        """Получить текущего пользователя"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)