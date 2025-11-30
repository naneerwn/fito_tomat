"""
ML Service для диагностики заболеваний томатов с использованием EfficientNet-B3.
Включает предобработку, инференс и генерацию тепловых карт через GRAD-CAM.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple, Optional

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import timm
from PIL import Image

from django.conf import settings


# Классы заболеваний (соответствуют порядку обучения модели)
DISEASE_CLASSES = [
    'Tomato Early blight leaf',
    'Tomato leaf',  # Здоровый
    'Tomato leaf bacterial spot',
    'Tomato leaf late blight',
    'Tomato leaf mosaic virus',
    'Tomato leaf yellow virus',
    'Tomato mold leaf',
    'Tomato Septoria leaf spot',
]

CLASS_TO_IDX = {cls: idx for idx, cls in enumerate(DISEASE_CLASSES)}
IDX_TO_CLASS = {idx: cls for cls, idx in CLASS_TO_IDX.items()}

# Параметры модели (из кода обучения)
IMG_SIZE = 300
NORMALIZE_MEAN = (0.485, 0.456, 0.406)
NORMALIZE_STD = (0.229, 0.224, 0.225)
MODEL_NAME = 'tf_efficientnet_b3.in1k'
NUM_CLASSES = len(DISEASE_CLASSES)


class TomatoDiseasePredictor:
    """Сервис для предсказания заболеваний томатов с использованием EfficientNet-B3."""

    def __init__(self, model_path: Optional[str] = None):
        """
        Инициализация сервиса.

        Параметры:
            model_path: Путь к файлу модели .pth. Если None, используется путь из settings.
        """
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.model_path = model_path or getattr(settings, 'ML_MODEL_PATH', None)
        
        if not self.model_path:
            # Путь по умолчанию
            base_dir = Path(settings.BASE_DIR)
            self.model_path = str(base_dir / 'best_effnet_b3.pth')
        
        self._load_model()

    def _load_model(self) -> None:
        """Загрузка обученной модели."""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Модель не найдена: {self.model_path}")
        
        # Создаем модель с той же архитектурой
        self.model = timm.create_model(
            MODEL_NAME,
            pretrained=False,
            num_classes=NUM_CLASSES,
        )
        
        # Загружаем веса
        state_dict = torch.load(self.model_path, map_location=self.device)
        self.model.load_state_dict(state_dict)
        self.model.to(self.device)
        self.model.eval()
        
        print(f"Модель загружена: {self.model_path}")

    def preprocess_image(self, image_path: str) -> torch.Tensor:
        """
        Предобработка изображения для инференса.

        Параметры:
            image_path: Путь к изображению.

        Возвращает:
            Тензор изображения [1, 3, 300, 300].
        """
        # Читаем через OpenCV для совместимости с кодом обучения
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Не удалось загрузить изображение: {image_path}")
        
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (IMG_SIZE, IMG_SIZE))
        
        # Нормализация
        img = img.astype(np.float32) / 255.0
        img = (img - np.array(NORMALIZE_MEAN)) / np.array(NORMALIZE_STD)
        
        # Преобразование в тензор [C, H, W]
        img_tensor = torch.from_numpy(img).permute(2, 0, 1).float()
        
        # Добавляем batch dimension
        img_tensor = img_tensor.unsqueeze(0)
        
        return img_tensor.to(self.device)

    def predict(self, image_path: str) -> Tuple[str, float, np.ndarray]:
        """
        Предсказание заболевания на изображении.

        Параметры:
            image_path: Путь к изображению.

        Возвращает:
            Tuple (название_заболевания, confidence, вероятности_всех_классов).
        """
        img_tensor = self.preprocess_image(image_path)
        
        with torch.no_grad():
            outputs = self.model(img_tensor)
            probabilities = F.softmax(outputs, dim=1)
            confidence, pred_idx = torch.max(probabilities, dim=1)
            
            pred_idx = pred_idx.item()
            confidence = confidence.item()
            probs = probabilities.cpu().numpy()[0]
        
        disease_name = IDX_TO_CLASS[pred_idx]
        
        return disease_name, confidence, probs

    def generate_gradcam(
        self,
        image_path: str,
        output_path: Optional[str] = None,
    ) -> np.ndarray:
        """
        Генерация тепловой карты через GRAD-CAM.

        Параметры:
            image_path: Путь к исходному изображению.
            output_path: Путь для сохранения результата. Если None, не сохраняется.

        Возвращает:
            Наложенная тепловая карта (RGB numpy array).
        """
        # Загружаем оригинальное изображение
        orig_img = cv2.imread(image_path)
        if orig_img is None:
            raise ValueError(f"Не удалось загрузить изображение: {image_path}")
        
        orig_img = cv2.cvtColor(orig_img, cv2.COLOR_BGR2RGB)
        orig_img_resized = cv2.resize(orig_img, (IMG_SIZE, IMG_SIZE))
        
        # Подготавливаем тензор
        img_tensor = self.preprocess_image(image_path)
        
        # Регистрируем хуки для перехвата градиентов и активаций
        gradients = []
        activations = []
        
        def backward_hook(module, grad_input, grad_output):
            gradients.append(grad_output[0])
        
        def forward_hook(module, input, output):
            activations.append(output)
        
        # Подключаемся к последнему сверточному слою EfficientNet
        target_layer = self.model.conv_head
        handle_b = target_layer.register_full_backward_hook(backward_hook)
        handle_f = target_layer.register_forward_hook(forward_hook)
        
        try:
            # Прямой проход
            output = self.model(img_tensor)
            pred_idx = output.argmax(dim=1)
            
            # Обратный проход
            self.model.zero_grad()
            output[0, pred_idx].backward()
            
            # Вычисляем веса
            grads = gradients[0].cpu().data.numpy()[0]  # [Каналы, H, W]
            fmaps = activations[0].cpu().data.numpy()[0]  # [Каналы, H, W]
            
            # Глобальное усреднение градиентов (Global Average Pooling)
            weights = np.mean(grads, axis=(1, 2))
            
            # Строим CAM
            cam = np.zeros(fmaps.shape[1:], dtype=np.float32)
            for i, w in enumerate(weights):
                cam += w * fmaps[i]
            
            # Применение ReLU и нормализация
            cam = np.maximum(cam, 0)
            cam = cv2.resize(cam, (IMG_SIZE, IMG_SIZE))
            cam = cam - np.min(cam)
            if np.max(cam) > 0:
                cam = cam / np.max(cam)
            
            # Применяем цветовую карту
            heatmap_colored = cv2.applyColorMap(
                np.uint8(255 * cam),
                cv2.COLORMAP_JET
            )
            heatmap_colored = cv2.cvtColor(heatmap_colored, cv2.COLOR_BGR2RGB)
            
            # Наложение на оригинал
            superimposed = np.uint8(0.6 * orig_img_resized + 0.4 * heatmap_colored)
            
            # Сохраняем, если указан путь
            if output_path:
                cv2.imwrite(output_path, cv2.cvtColor(superimposed, cv2.COLOR_RGB2BGR))
            
            return superimposed
            
        finally:
            # Удаляем хуки
            handle_b.remove()
            handle_f.remove()


# Глобальный экземпляр сервиса (singleton)
_predictor_instance: Optional[TomatoDiseasePredictor] = None


def get_predictor() -> TomatoDiseasePredictor:
    """Получить экземпляр сервиса (singleton pattern)."""
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = TomatoDiseasePredictor()
    return _predictor_instance

