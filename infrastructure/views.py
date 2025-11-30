from __future__ import annotations

from typing import cast

from django.db.models import QuerySet
from rest_framework import permissions, viewsets
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from common.audit import AuditLoggingMixin
from common.typing import RequestWithUser, RoleAwareUser
from .models import Greenhouse, Section
from .serializers import GreenhouseSerializer, SectionSerializer


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request: RequestWithUser, view) -> bool:
        if request.method in permissions.SAFE_METHODS:  # GET, HEAD, OPTIONS - безопасные методы
            return True
        user = cast(RoleAwareUser, getattr(request, "user", None))
        return bool(user and user.is_staff)  # Изменять может только персонал/админ


@extend_schema(
    tags=['Инфраструктура'],
    description='Управление теплицами. Все авторизованные пользователи могут просматривать информацию, изменять могут только администраторы.'
)
class GreenhouseViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    """
    ViewSet для управления теплицами.
    
    - GET /api/greenhouses/ - получить список всех теплиц
    - GET /api/greenhouses/{id}/ - получить информацию о конкретной теплице
    - POST /api/greenhouses/ - создать новую теплицу (требуется роль Администратор)
    - PUT /api/greenhouses/{id}/ - обновить теплицу (требуется роль Администратор)
    - PATCH /api/greenhouses/{id}/ - частично обновить теплицу (требуется роль Администратор)
    - DELETE /api/greenhouses/{id}/ - удалить теплицу (требуется роль Администратор)
    
    Права доступа:
    - Просмотр: все авторизованные пользователи
    - Изменение: только администраторы
    """
    queryset = Greenhouse.objects.all().order_by('name')
    serializer_class = GreenhouseSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]  # Реализация прав из ТЗ

    def get_queryset(self) -> QuerySet[Greenhouse]:
        return self.queryset


@extend_schema(
    tags=['Инфраструктура'],
    description='Управление секциями теплиц. Все авторизованные пользователи могут просматривать информацию, изменять могут только администраторы.'
)
class SectionViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    """
    ViewSet для управления секциями теплиц.
    
    - GET /api/sections/ - получить список всех секций
    - GET /api/sections/{id}/ - получить информацию о конкретной секции
    - POST /api/sections/ - создать новую секцию (требуется роль Администратор)
    - PUT /api/sections/{id}/ - обновить секцию (требуется роль Администратор)
    - PATCH /api/sections/{id}/ - частично обновить секцию (требуется роль Администратор)
    - DELETE /api/sections/{id}/ - удалить секцию (требуется роль Администратор)
    
    Права доступа:
    - Просмотр: все авторизованные пользователи
    - Изменение: только администраторы
    """
    queryset = Section.objects.all()
    serializer_class = SectionSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    def get_queryset(self) -> QuerySet[Section]:
        return self.queryset
