from django.db import models

class Greenhouse(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название")
    location = models.CharField(max_length=255, verbose_name="Местоположение")

    class Meta:
        db_table = 'greenhouses'  # [cite: 803]
        verbose_name = 'Теплица'
        verbose_name_plural = 'Теплицы'

    def __str__(self):
        return self.name

class Section(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название секции")
    description = models.TextField(blank=True, verbose_name="Описание")
    greenhouse = models.ForeignKey(Greenhouse, on_delete=models.CASCADE, related_name='sections', verbose_name="Теплица")

    class Meta:
        db_table = 'sections'  # [cite: 804]
        verbose_name = 'Секция'
        verbose_name_plural = 'Секции'

    def __str__(self):
        return f"{self.greenhouse.name} - {self.name}"