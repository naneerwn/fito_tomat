"""
Фабрика для создания и управления ML-моделями для диагностики заболеваний.
"""

from __future__ import annotations

from typing import Protocol, Optional, Any, Tuple
from enum import Enum
from pathlib import Path

from django.conf import settings

from diagnostics.ml_service.ml_service import get_predictor as get_effnet_predictor
from diagnostics.ml_service.custom_cnn_service import get_custom_cnn_predictor
from diagnostics.ml_service.vit_service import get_vit_predictor
from diagnostics.ml_service.yolo_service import get_yolo_predictor


class MLModelType(str, Enum):
    """Типы доступных ML-моделей."""
    EFFNET = 'effnet'
    CUSTOM_CNN = 'custom_cnn'
    VIT = 'vit'
    YOLO = 'yolo'


class PredictorProtocol(Protocol):
    """Протокол для всех предикторов."""
    
    def predict(self, image_path: str) -> Tuple[str, float, Any]:
        """Предсказание заболевания."""
        ...
    
    def generate_gradcam(self, image_path: str, output_path: Optional[str] = None) -> Any:
        """Генерация тепловой карты (GRAD-CAM)."""
        ...
    
    def generate_attention_map(self, image_path: str, output_path: Optional[str] = None) -> Any:
        """Генерация тепловой карты (attention map для ViT)."""
        ...


def get_predictor(model_type: Optional[str] = None) -> PredictorProtocol:
    """
    Получить предиктор для указанного типа модели.
    
    Параметры:
        model_type: Тип модели ('effnet', 'custom_cnn', 'vit', 'yolo').
                   Если None, используется DEFAULT_ML_MODEL из settings.
    
    Возвращает:
        Экземпляр предиктора.
    
    Исключения:
        ValueError: Если указан неизвестный тип модели.
    """
    if model_type is None:
        model_type = getattr(settings, 'DEFAULT_ML_MODEL', 'effnet')
    
    model_type = model_type.lower()
    
    if model_type == MLModelType.EFFNET:
        return get_effnet_predictor()
    elif model_type == MLModelType.CUSTOM_CNN:
        return get_custom_cnn_predictor()
    elif model_type == MLModelType.VIT:
        return get_vit_predictor()
    elif model_type == MLModelType.YOLO:
        return get_yolo_predictor()
    else:
        raise ValueError(
            f"Неизвестный тип модели: {model_type}. "
            f"Доступные типы: {', '.join([m.value for m in MLModelType])}"
        )


def generate_heatmap(predictor: PredictorProtocol, image_path: str, output_path: Optional[str] = None) -> Any:
    """
    Генерация тепловой карты/визуализации с использованием соответствующего метода для модели.
    
    Параметры:
        predictor: Экземпляр предиктора.
        image_path: Путь к изображению.
        output_path: Путь для сохранения результата.
    
    Возвращает:
        Визуализация (RGB numpy array):
        - Для ViT: attention map
        - Для YOLO: изображение с bounding boxes
        - Для остальных: GRAD-CAM heatmap
    """
    # Для ViT используем generate_attention_map
    if hasattr(predictor, 'generate_attention_map'):
        return predictor.generate_attention_map(image_path, output_path)
    # Для YOLO и остальных используем generate_gradcam
    # (YOLO переопределяет generate_gradcam для отрисовки bounding boxes)
    else:
        return predictor.generate_gradcam(image_path, output_path)

