import json
from pathlib import Path
from typing import cast
from datetime import timedelta

from django.db.models import QuerySet
import io
from django.http import FileResponse, Http404, HttpResponse
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from django.utils import dateparse, timezone

from common.audit import AuditLoggingMixin
from common.typing import RoleAwareUser
from django.conf import settings
from .models import AuditLog, Report
from .serializers import AuditLogSerializer, ReportSerializer
from .services import (
    build_excel_report,
    build_pdf_report,
    build_report_payload_by_type,
    fetch_detailed_data,
    generate_report_payload,
    persist_report_file,
)


@extend_schema(
    tags=['Отчеты'],
    description='Управление отчетами системы. Позволяет создавать отчеты за указанный период и скачивать их в формате JSON.'
)
class ReportViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    """
    ViewSet для управления отчетами системы.
    
    - GET /api/reports/ - получить список отчетов (пользователи видят только свои, админы - все)
    - GET /api/reports/{id}/ - получить информацию о конкретном отчете
    - POST /api/reports/ - создать новый отчет за указанный период
    - PUT /api/reports/{id}/ - обновить отчет
    - PATCH /api/reports/{id}/ - частично обновить отчет
    - DELETE /api/reports/{id}/ - удалить отчет
    - GET /api/reports/{id}/download/ - скачать файл отчета в формате JSON
    
    При создании отчета автоматически генерируется JSON файл с данными за указанный период.
    """
    queryset = Report.objects.select_related('user').all().order_by('-generated_at')
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet[Report]:
        user = cast(RoleAwareUser, self.request.user)
        if user.is_staff or (user.role and user.role.name == 'Администратор'):
            return self.queryset
        return self.queryset.filter(user=user)

    def perform_create(self, serializer: ReportSerializer) -> None:
        report_type = serializer.validated_data['report_type']
        payload = build_report_payload_by_type(
            serializer.validated_data['period_start'],
            serializer.validated_data['period_end'],
            report_type,
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

    @extend_schema(
        summary='Скачать файл отчета',
        description='Скачивает JSON файл отчета по указанному ID',
        tags=['Отчеты']
    )
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

    @extend_schema(
        summary='Скачать отчет в Excel (XLSX)',
        description='Генерирует XLSX с плоским представлением key/value данных отчета.',
        tags=['Отчеты']
    )
    @action(detail=True, methods=['get'], url_path='download-excel')
    def download_excel(self, request, pk=None):
        """Скачать отчет в XLSX (оформленные таблицы)."""
        report = self.get_object()
        start_dt, end_dt = report.period_start, report.period_end
        user = cast(RoleAwareUser, report.user)
        reporter = user.full_name if getattr(user, 'full_name', '') else user.username
        reporter_role = getattr(getattr(user, 'role', None), 'name', '')
        details = fetch_detailed_data(start_dt, end_dt)
        summary = build_report_payload_by_type(start_dt, end_dt, report.report_type)

        wb = build_excel_report(report, details, summary, reporter, reporter_role)
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        response = HttpResponse(
            buf.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="report_{report.id}.xlsx"'
        return response

    @extend_schema(
        summary='Скачать отчет в PDF',
        description='Генерирует простой PDF с ключами и значениями отчета.',
        tags=['Отчеты']
    )
    @action(detail=True, methods=['get'], url_path='download-pdf')
    def download_pdf(self, request, pk=None):
        """Скачать отчет в PDF (таблицы)."""
        report = self.get_object()
        start_dt, end_dt = report.period_start, report.period_end
        user = cast(RoleAwareUser, report.user)
        reporter = user.full_name if getattr(user, 'full_name', '') else user.username
        reporter_role = getattr(getattr(user, 'role', None), 'name', '')

        details = fetch_detailed_data(start_dt, end_dt)
        summary = build_report_payload_by_type(start_dt, end_dt, report.report_type)

        pdf = build_pdf_report(report, details, summary, reporter, reporter_role)
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="report_{report.id}.pdf"'
        return response

    @extend_schema(
        summary='Онлайн сводка (живые данные)',
        description='Возвращает агрегированные KPI напрямую из БД за указанный период. Параметры: period_start, period_end (ISO). Если не заданы — последние 30 дней.',
        tags=['Отчеты']
    )
    @action(detail=False, methods=['get'], url_path='live-summary')
    def live_summary(self, request):
        """Живая сводка дашборда без предварительной генерации отчёта."""
        period_start_str = request.query_params.get('period_start')
        period_end_str = request.query_params.get('period_end')

        now = timezone.now()
        default_start = now - timedelta(days=30)

        def parse_dt(val, fallback):
            if not val:
                return fallback
            dt = dateparse.parse_datetime(val)
            if dt is None:
                return fallback
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.get_current_timezone())
            return dt

        start_dt = parse_dt(period_start_str, default_start)
        end_dt = parse_dt(period_end_str, now)

        payload = generate_report_payload(start_dt, end_dt)
        return Response(payload)


@extend_schema(
    tags=['Отчеты'],
    description='Просмотр журнала аудита системы. Доступно только администраторам. Содержит историю всех изменений в системе.'
)
class AuditLogViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    ViewSet для просмотра журнала аудита системы.
    
    - GET /api/audit-logs/ - получить список записей журнала аудита (требуется роль Администратор)
    - GET /api/audit-logs/{id}/ - получить информацию о конкретной записи аудита (требуется роль Администратор)
    
    Журнал аудита содержит информацию о всех изменениях в системе:
    - Кто выполнил действие
    - Какое действие было выполнено (создание, обновление, удаление)
    - Какая таблица была изменена
    - Старые и новые значения полей
    
    Доступ: только администраторы системы.
    """
    queryset = AuditLog.objects.select_related('user').all().order_by('-created_at')
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminUser]
