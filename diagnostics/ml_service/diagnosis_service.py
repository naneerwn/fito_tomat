"""
Сервис для автоматической диагностики заболеваний при загрузке изображений.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

from diagnostics.models import Disease, Diagnosis, Image
from diagnostics.ml_service.ml_service import get_predictor, DISEASE_CLASSES


def ensure_diseases_in_db() -> None:
    """
    Убедиться, что все классы заболеваний из ML-модели есть в БД.
    Создает записи, если их нет.
    """
    for disease_name in DISEASE_CLASSES:
        Disease.objects.get_or_create(
            name=disease_name,
            defaults={
                'description': f'Автоматически создано для класса "{disease_name}"',
                'symptoms': 'Требуется заполнение агрономом',
            }
        )


def run_ml_diagnosis(image_instance: Image) -> Optional[Diagnosis]:
    """
    Запустить ML-диагностику для загруженного изображения.

    Параметры:
        image_instance: Экземпляр модели Image.

    Возвращает:
        Созданный Diagnosis или None в случае ошибки.
    """
    try:
        # Убеждаемся, что все заболевания есть в БД
        ensure_diseases_in_db()
        
        # Получаем путь к файлу
        image_path = image_instance.file_path.path
        
        if not os.path.exists(image_path):
            print(f"Файл изображения не найден: {image_path}")
            return None
        
        # Получаем ML-сервис
        predictor = get_predictor()
        
        # Предсказание
        disease_name, confidence, probs = predictor.predict(image_path)
        
        # Находим заболевание в БД
        try:
            disease = Disease.objects.get(name=disease_name)
        except Disease.DoesNotExist:
            print(f"Заболевание '{disease_name}' не найдено в БД")
            return None
        
        # Генерируем тепловую карту
        heatmap_filename = f'heatmap_{image_instance.id}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.jpg'
        
        # Генерируем тепловую карту (без сохранения на диск)
        heatmap_array = predictor.generate_gradcam(image_path, None)
        
        # Создаем диагноз (сохраняем изначальный диагноз ML в ml_disease)
        diagnosis = Diagnosis.objects.create(
            image=image_instance,
            disease=disease,
            ml_disease=disease,  # Сохраняем изначальный диагноз от ML
            confidence=confidence,
            is_verified=False,
            timestamp=timezone.now(),
        )
        
        # Сохраняем тепловую карту через PIL в ContentFile
        from PIL import Image as PILImage
        import io
        
        heatmap_pil = PILImage.fromarray(heatmap_array)
        buffer = io.BytesIO()
        heatmap_pil.save(buffer, format='JPEG', quality=95)
        buffer.seek(0)
        
        diagnosis.heatmap_path.save(
            heatmap_filename,
            ContentFile(buffer.read()),
            save=True
        )
        
        print(f"Диагноз создан: {disease_name} (confidence: {confidence:.2%})")
        return diagnosis
        
    except Exception as e:
        print(f"Ошибка при ML-диагностике: {e}")
        import traceback
        traceback.print_exc()
        return None

