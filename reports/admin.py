from django.contrib import admin
from .models import Report, AuditLog


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('report_type', 'user', 'generated_at')
    list_filter = ('report_type', 'generated_at')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action_type', 'user', 'table_name', 'record_id', 'created_at')
    list_filter = ('action_type', 'table_name', 'created_at')
    search_fields = ('old_values', 'new_values')

    # Запрещаем редактирование и удаление логов через админку (Безопасность)
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    # Удаление логов тоже лучше запретить или оставить только суперюзеру
    # def has_delete_permission(self, request, obj=None):
    #    return False