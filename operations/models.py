from django.db import models
from users.models import User
from diagnostics.models import Diagnosis

class Recommendation(models.Model):
    diagnosis = models.ForeignKey(Diagnosis, on_delete=models.CASCADE, related_name='recommendations', verbose_name="Диагноз")
    agronomist = models.ForeignKey(User, on_delete=models.PROTECT, related_name='issued_recommendations', verbose_name="Агроном")
    treatment_plan_text = models.TextField(verbose_name="План лечения")
    status = models.CharField(max_length=50, verbose_name="Статус")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        db_table = 'recommendations'  # [cite: 809]
        verbose_name = 'Рекомендация'
        verbose_name_plural = 'Рекомендации'

class Task(models.Model):
    recommendation = models.ForeignKey(Recommendation, on_delete=models.CASCADE, related_name='tasks', verbose_name="Рекомендация")
    operator = models.ForeignKey(User, on_delete=models.PROTECT, related_name='tasks', verbose_name="Исполнитель")
    description = models.TextField(verbose_name="Описание задачи")
    status = models.CharField(max_length=50, verbose_name="Статус")
    deadline = models.DateTimeField(verbose_name="Срок исполнения")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Завершено")

    class Meta:
        db_table = 'tasks'  # [cite: 810]
        verbose_name = 'Задача'
        verbose_name_plural = 'Задачи'
        ordering = ['-created_at']  # Сортировка по дате создания (новые сверху)