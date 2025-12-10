from django.db import models
# Импортируем модели из других приложений
from users.models import User
from infrastructure.models import Section

class Disease(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название болезни")
    description = models.TextField(verbose_name="Описание")
    symptoms = models.TextField(verbose_name="Симптомы")

    class Meta:
        db_table = 'diseases'  # [cite: 806]
        verbose_name = 'Заболевание'
        verbose_name_plural = 'Заболевания'
        ordering = ['name']

    def __str__(self):
        return self.name

class Treatment(models.Model):
    disease = models.ForeignKey(Disease, on_delete=models.CASCADE, related_name='treatments', verbose_name="Заболевание")
    name = models.CharField(max_length=255, verbose_name="Название препарата/метода")
    description = models.TextField(verbose_name="Описание лечения")
    dosage = models.CharField(max_length=255, verbose_name="Дозировка")
    precautions = models.TextField(verbose_name="Меры предосторожности")

    class Meta:
        db_table = 'treatments'  # [cite: 808]
        verbose_name = 'Метод лечения'
        verbose_name_plural = 'Методы лечения'

class Image(models.Model):
    section = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True, verbose_name="Секция")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Загрузил")
    file_path = models.ImageField(upload_to='plants/%Y/%m/%d/', verbose_name="Путь к файлу") # Django сам сохранит путь
    file_format = models.CharField(max_length=10, verbose_name="Формат")
    camera_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="ID камеры")
    timestamp = models.DateTimeField(verbose_name="Время съемки", auto_now_add=True)
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Время загрузки")

    class Meta:
        db_table = 'images'
        verbose_name = 'Изображение'
        verbose_name_plural = 'Изображения'
        ordering = ['-timestamp']

class Diagnosis(models.Model):
    image = models.ForeignKey(Image, on_delete=models.CASCADE, related_name='diagnoses', verbose_name="Изображение")
    disease = models.ForeignKey(Disease, on_delete=models.PROTECT, verbose_name="Заболевание")
    ml_disease = models.ForeignKey(Disease, on_delete=models.PROTECT, null=True, blank=True, related_name='ml_diagnoses', verbose_name="Изначальный диагноз ML")
    confidence = models.FloatField(verbose_name="Уверенность модели")
    model_type = models.CharField(max_length=50, null=True, blank=True, verbose_name="Тип ML-модели", help_text="Тип модели, использованной для диагностики: effnet, custom_cnn, vit, yolo")
    model_accuracy = models.FloatField(null=True, blank=True, verbose_name="Точность модели", help_text="Точность модели на тестовом наборе (в процентах)")
    is_verified = models.BooleanField(default=False, verbose_name="Верифицировано")
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_diagnoses', verbose_name="Кто проверил")
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата проверки")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Время создания")
    heatmap_path = models.ImageField(upload_to='heatmaps/%Y/%m/%d/', null=True, blank=True, verbose_name="Тепловая карта")

    class Meta:
        db_table = 'diagnoses'  # [cite: 807]
        verbose_name = 'Диагноз'
        verbose_name_plural = 'Диагнозы'
        ordering = ['-timestamp', '-id']