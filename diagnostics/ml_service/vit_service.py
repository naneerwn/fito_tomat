"""
ML Service для диагностики заболеваний томатов с использованием Vision Transformer (ViT).
Включает предобработку, инференс и генерацию тепловых карт через attention visualization.
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
IMG_SIZE = 224  # ViT использует 224x224
NORMALIZE_MEAN = (0.485, 0.456, 0.406)
NORMALIZE_STD = (0.229, 0.224, 0.225)
VIT_MODEL_NAME = 'vit_base_patch16_224.augreg2_in21k_ft_in1k'
NUM_CLASSES = len(DISEASE_CLASSES)


class ViTPredictor:
    """Сервис для предсказания заболеваний томатов с использованием Vision Transformer."""

    def __init__(self, model_path: Optional[str] = None):
        """
        Инициализация сервиса.

        Параметры:
            model_path: Путь к файлу модели .pth. Если None, используется путь из settings.
        """
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.model_path = model_path or getattr(settings, 'VIT_MODEL_PATH', None)
        
        if not self.model_path:
            # Путь по умолчанию
            base_dir = Path(settings.BASE_DIR)
            self.model_path = str(base_dir / 'models' / 'ViT-Base_best.pth')
        
        self._load_model()

    def _load_model(self) -> None:
        """Загрузка обученной модели."""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Модель не найдена: {self.model_path}")
        
        # Создаем модель с той же архитектурой
        self.model = timm.create_model(
            VIT_MODEL_NAME,
            pretrained=False,
            num_classes=NUM_CLASSES,
            img_size=IMG_SIZE,
        )
        
        # Загружаем веса
        state_dict = torch.load(self.model_path, map_location=self.device)
        self.model.load_state_dict(state_dict)
        self.model.to(self.device)
        self.model.eval()
        
        print(f"ViT модель загружена: {self.model_path}")

    def preprocess_image(self, image_path: str) -> torch.Tensor:
        """
        Предобработка изображения для инференса.

        Параметры:
            image_path: Путь к изображению.

        Возвращает:
            Тензор изображения [1, 3, 224, 224].
        """
        # Читаем через OpenCV для совместимости с кодом обучения
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Не удалось загрузить изображение: {image_path}")
        
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (IMG_SIZE, IMG_SIZE))
        
        # Нормализация (как в коде обучения)
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

    def generate_attention_map(
        self,
        image_path: str,
        output_path: Optional[str] = None,
    ) -> np.ndarray:
        """
        Генерация тепловой карты через attention visualization для ViT.

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
        
        # Регистрируем хуки для перехвата attention weights
        attention_weights = []
        
        def attention_hook(module, input, output):
            # Для timm ViT, attention weights могут быть в output
            if isinstance(output, tuple) and len(output) > 1:
                attn = output[1]  # attention weights обычно во втором элементе
                if attn is not None:
                    attention_weights.append(attn.cpu().detach())
        
        # Регистрируем хуки на attention блоках
        handles = []
        for name, module in self.model.named_modules():
            if 'attn' in name and hasattr(module, 'qkv'):
                handle = module.register_forward_hook(attention_hook)
                handles.append(handle)
        
        try:
            # Прямой проход
            output = self.model(img_tensor)
            pred_idx = output.argmax(dim=1)
            
            # Если не удалось получить attention weights, используем альтернативный метод
            if not attention_weights:
                # Используем активации из промежуточных слоев
                attention_map = self._get_activation_map(img_tensor)
            else:
                # Используем последние attention weights
                # Берем среднее по всем attention heads
                attn = attention_weights[-1]  # [batch, heads, patches, patches]
                if len(attn.shape) == 4:
                    # Берем attention к CLS token (первый патч)
                    attn_to_cls = attn[0, :, 0, 1:].mean(dim=0)  # [patches]
                    # Преобразуем в heatmap
                    grid_size = int(np.sqrt(attn_to_cls.shape[0]))
                    attention_map = attn_to_cls.reshape(grid_size, grid_size).numpy()
                    attention_map = cv2.resize(attention_map, (IMG_SIZE, IMG_SIZE))
                else:
                    attention_map = self._get_activation_map(img_tensor)
            
            # Нормализация
            attention_map = (attention_map - attention_map.min()) / (attention_map.max() - attention_map.min() + 1e-8)
            
            # Применяем цветовую карту
            heatmap_colored = cv2.applyColorMap(
                np.uint8(255 * attention_map),
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
            for handle in handles:
                handle.remove()
    
    def generate_gradcam(
        self,
        image_path: str,
        output_path: Optional[str] = None,
    ) -> np.ndarray:
        """
        Алиас для generate_attention_map для совместимости с другими моделями.
        
        Параметры:
            image_path: Путь к исходному изображению.
            output_path: Путь для сохранения результата. Если None, не сохраняется.

        Возвращает:
            Наложенная тепловая карта (RGB numpy array).
        """
        return self.generate_attention_map(image_path, output_path)
    
    def _get_activation_map(self, img_tensor: torch.Tensor) -> np.ndarray:
        """
        Альтернативный метод получения activation map для ViT.
        Использует промежуточные активации модели.
        """
        activations = []
        
        def forward_hook(module, input, output):
            activations.append(output.cpu().detach())
        
        # Цепляемся к промежуточным блокам
        handles = []
        for i, block in enumerate(self.model.blocks[:4]):  # Используем первые 4 блока
            handle = block.register_forward_hook(forward_hook)
            handles.append(handle)
        
        try:
            with torch.no_grad():
                # Получаем патчи
                x = self.model.patch_embed(img_tensor)
                cls_token = self.model.cls_token.expand(x.shape[0], -1, -1)
                x = torch.cat((cls_token, x), dim=1)
                x = x + self.model.pos_embed
                
                # Проходим через блоки
                for block in self.model.blocks[:4]:
                    x = block(x)
            
            # Используем активации без CLS токена
            if activations:
                features = activations[-1][:, 1:].mean(dim=-1).numpy()[0]  # [patches]
                grid_size = int(np.sqrt(features.shape[0]))
                attention_map = features.reshape(grid_size, grid_size)
                attention_map = cv2.resize(attention_map, (IMG_SIZE, IMG_SIZE))
            else:
                # Fallback: равномерная карта
                attention_map = np.ones((IMG_SIZE, IMG_SIZE)) * 0.5
            
            return attention_map
            
        finally:
            for handle in handles:
                handle.remove()


# Глобальный экземпляр сервиса (singleton)
_vit_instance: Optional[ViTPredictor] = None


def get_vit_predictor() -> ViTPredictor:
    """Получить экземпляр сервиса (singleton pattern)."""
    global _vit_instance
    if _vit_instance is None:
        _vit_instance = ViTPredictor()
    return _vit_instance

