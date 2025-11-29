from __future__ import annotations

from typing import cast

from django.db.models import QuerySet
from rest_framework import permissions, viewsets
from rest_framework.permissions import IsAuthenticated

from common.audit import AuditLoggingMixin
from common.typing import RequestWithUser, RoleAwareUser
from .models import Greenhouse, Section
from .serializers import GreenhouseSerializer, SectionSerializer


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request: RequestWithUser, view) -> bool:
        if request.method in permissions.SAFE_METHODS:  # GET, HEAD, OPTIONS
            return True
        user = cast(RoleAwareUser, getattr(request, "user", None))
        return bool(user and user.is_staff)  # Изменять может только персонал/админ


class GreenhouseViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = Greenhouse.objects.all().order_by('name')
    serializer_class = GreenhouseSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]  # Реализация прав из ТЗ

    def get_queryset(self) -> QuerySet[Greenhouse]:
        return self.queryset


class SectionViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = Section.objects.all()
    serializer_class = SectionSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    def get_queryset(self) -> QuerySet[Section]:
        return self.queryset
