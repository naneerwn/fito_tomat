from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import User, Role
from .serializers import UserSerializer, RoleSerializer
from common.audit import AuditLoggingMixin

class RoleViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAdminUser] # Только админ управляет ролями

class UserViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('id')
    serializer_class = UserSerializer

    def get_permissions(self):
        # Удаление пользователей - только админ
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        # Админ видит всех, остальные - только себя (специфика безопасности)
        if user.is_staff or (user.role and user.role.name == 'Администратор'):
            return self.queryset
        return self.queryset.filter(id=user.id)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Получить текущего пользователя"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)