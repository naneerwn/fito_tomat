import json

from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from common.audit import AuditLoggingMixin
from .models import Report, AuditLog
from .serializers import ReportSerializer, AuditLogSerializer
from .services import generate_report_payload, persist_report_file


class ReportViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = Report.objects.select_related('user').all().order_by('-generated_at')
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or (user.role and user.role.name == 'Администратор'):
            return self.queryset
        return self.queryset.filter(user=user)

    def perform_create(self, serializer):
        payload = generate_report_payload(
            serializer.validated_data['period_start'],
            serializer.validated_data['period_end'],
        )
        instance = self.save_and_log_create(
            serializer,
            user=self.request.user,
            data=json.dumps(payload, ensure_ascii=False),
            file_path='',
        )
        report_file = persist_report_file(instance.id, payload)
        instance.file_path = str(report_file)
        instance.save(update_fields=['file_path'])


class AuditLogViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = AuditLog.objects.select_related('user').all().order_by('-created_at')
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminUser]
