from django.db import models
from users.models import User

class Report(models.Model):
    user = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="Создатель")
    report_type = models.CharField(max_length=100, verbose_name="Тип отчета")
    period_start = models.DateTimeField(verbose_name="Начало периода")
    period_end = models.DateTimeField(verbose_name="Конец периода")
    data = models.TextField(verbose_name="Данные отчета") # Храним JSON или текст
    generated_at = models.DateTimeField(auto_now_add=True, verbose_name="Сгенерировано")
    file_path = models.CharField(max_length=500, verbose_name="Путь к файлу")

    class Meta:
        db_table = 'reports'  # [cite: 811]
        verbose_name = 'Отчет'
        verbose_name_plural = 'Отчеты'

class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Пользователь")
    action_type = models.CharField(max_length=50, verbose_name="Тип действия")
    table_name = models.CharField(max_length=100, verbose_name="Таблица")
    record_id = models.IntegerField(verbose_name="ID записи")
    old_values = models.TextField(null=True, blank=True, verbose_name="Старые значения")
    new_values = models.TextField(null=True, blank=True, verbose_name="Новые значения")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Время действия")

    class Meta:
        db_table = 'audit_log'  # [cite: 812]
        verbose_name = 'Журнал аудита'
        verbose_name_plural = 'Журнал аудита'