import json
from pathlib import Path
from typing import cast

from django.db.models import QuerySet
from django.http import FileResponse, Http404
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from common.audit import AuditLoggingMixin
from common.typing import RoleAwareUser
from django.conf import settings
from .models import AuditLog, Report
from .serializers import AuditLogSerializer, ReportSerializer
from .services import generate_report_payload, persist_report_file


class ReportViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = Report.objects.select_related('user').all().order_by('-generated_at')
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet[Report]:
        user = cast(RoleAwareUser, self.request.user)
        if user.is_staff or (user.role and user.role.name == 'Администратор'):
            return self.queryset
        return self.queryset.filter(user=user)

    def perform_create(self, serializer: ReportSerializer) -> None:
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

    @action(detail=True, methods=['get'], url_path='download')
    def download(self, request, pk=None):
        """Скачать файл отчёта."""
        report = self.get_object()
        if not report.file_path:
            raise Http404('Файл отчёта не найден')
        
        file_path = Path(report.file_path)
        if not file_path.exists():
            raise Http404('Файл отчёта не существует на сервере')
        
        return FileResponse(
            open(file_path, 'rb'),
            as_attachment=True,
            filename=f'report_{report.id}.json',
            content_type='application/json',
        )


class AuditLogViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = AuditLog.objects.select_related('user').all().order_by('-created_at')
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminUser]
