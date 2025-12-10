from __future__ import annotations

import logging
from typing import Optional

from django.db import transaction

from .ml_service.diagnosis_service import run_ml_diagnosis
from .models import Diagnosis, Image

logger = logging.getLogger(__name__)


def trigger_auto_diagnosis(image: Image, model_type: Optional[str] = None) -> None:
    """
    Запускает автоматическую ML-диагностику после загрузки изображения.
    Ошибки логируются, но не пробрасываются — создание изображения не блокируется.
    """
    try:
        run_ml_diagnosis(image, model_type=model_type)
    except Exception:
        logger.exception("Ошибка при автоматической диагностике image_id=%s", getattr(image, "id", None))


def recreate_diagnosis_with_model(diagnosis: Diagnosis, model_type: str) -> Diagnosis:
    """
    Пересоздаёт диагноз с новой моделью в транзакции:
    - удаляет старый диагноз
    - создаёт новый на основе того же изображения
    """
    with transaction.atomic():
        image_instance = diagnosis.image
        diagnosis.delete()
        new_diagnosis = run_ml_diagnosis(image_instance, model_type=model_type)
        return new_diagnosis

