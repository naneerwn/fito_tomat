from rest_framework import viewsets, permissions
from rest_framework.permissions import IsAuthenticated

from .models import Greenhouse, Section
from .serializers import GreenhouseSerializer, SectionSerializer
from common.audit import AuditLoggingMixin

class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS: # GET, HEAD, OPTIONS
            return True
        return request.user.is_staff # Изменять может только персонал/админ

class GreenhouseViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = Greenhouse.objects.all().order_by('name')
    serializer_class = GreenhouseSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly] # Реализация прав из ТЗ

class SectionViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = Section.objects.all()
    serializer_class = SectionSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]