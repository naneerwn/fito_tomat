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
from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.image import show_cam_on_image

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
        # GradCAM инициализируется лениво
        self._cam: Optional[GradCAM] = None

    @staticmethod
    def _reshape_transform(tensor: torch.Tensor, height: int = 14, width: int = 14) -> torch.Tensor:
        """
        Преобразование выхода ViT к формату [B, C, H, W], который ожидает grad-cam.

        tensor: [B, N_tokens, C], где N_tokens = 1 (CLS) + H*W.
        """
        # Убираем CLS-токен
        result = tensor[:, 1:, :]  # [B, H*W, C]
        # Собираем обратно в сетку патчей
        result = result.reshape(tensor.size(0), height, width, tensor.size(2))  # [B, H, W, C]
        # Преобразуем в [B, C, H, W]
        result = result.permute(0, 3, 1, 2).contiguous()
        return result

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
        Для ViT используем тот же Grad-CAM, что и для других моделей,
        но с reshape_transform для токенов трансформера.
        """
        return self.generate_gradcam(image_path=image_path, output_path=output_path)
    
    def generate_gradcam(
        self,
        image_path: str,
        output_path: Optional[str] = None,
    ) -> np.ndarray:
        """
        Генерация тепловой карты для ViT с использованием Grad-CAM
        через библиотеку `pytorch-grad-cam`.
        """
        # Загружаем оригинальное изображение
        orig_img = cv2.imread(image_path)
        if orig_img is None:
            raise ValueError(f"Не удалось загрузить изображение: {image_path}")

        orig_img = cv2.cvtColor(orig_img, cv2.COLOR_BGR2RGB)
        orig_h, orig_w = orig_img.shape[:2]

        # Подготавливаем тензор
        img_tensor = self.preprocess_image(image_path)

        # Инициализируем GradCAM один раз и переиспользуем
        if self._cam is None:
            # Целевой слой: нормализация последнего блока трансформера,
            # как в рекомендованных примерах для ViT.
            target_layers = [self.model.blocks[-1].norm1]
            # В используемой версии pytorch-grad-cam параметр use_cuda отсутствует,
            # устройство определяется по модели и входу.
            self._cam = GradCAM(
                model=self.model,
                target_layers=target_layers,
                reshape_transform=self._reshape_transform,
            )

        self.model.eval()
        grayscale_cam = self._cam(input_tensor=img_tensor, targets=None)

        # Берём первую карту из батча
        grayscale_cam = grayscale_cam[0]
        if grayscale_cam.shape != (orig_h, orig_w):
            grayscale_cam = cv2.resize(grayscale_cam, (orig_w, orig_h))

        # Нормализуем карту в диапазон [0, 1]
        grayscale_cam = np.clip(grayscale_cam, 0.0, 1.0)

        # Жёстко убираем фон: всё, что ниже порога, зануляем,
        # чтобы подсвечивались только наиболее выраженные зоны поражения.
        soft_threshold = 0.0  # можно подстроить в диапазоне 0.5–0.7
        low_mask = grayscale_cam < soft_threshold
        grayscale_cam[low_mask] = 0.0

        # Наложение на оригинальное изображение:
        # используем JET для ярких красно-оранжевых зон,
        # но делаем фон почти прозрачным за счёт переменной альфы.
        rgb_img_float = orig_img.astype(np.float32) / 255.0

        heatmap = cv2.applyColorMap(
            np.uint8(255 * grayscale_cam),
            cv2.COLORMAP_JET,
        )
        heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0

        # Альфа зависит от значения CAM: фон (0) полностью прозрачен,
        # сильные активации — до 0.6.
        alpha_min, alpha_max = 0.0, 0.6
        alpha = alpha_min + (alpha_max - alpha_min) * grayscale_cam  # [H, W] в [0.1, 0.6]
        alpha = alpha[..., None]  # приводим к [H, W, 1] для корректного broadcasting

        blended = (1.0 - alpha) * rgb_img_float + alpha * heatmap
        superimposed = np.uint8(255 * np.clip(blended, 0.0, 1.0))

        if output_path:
            cv2.imwrite(output_path, cv2.cvtColor(superimposed, cv2.COLOR_RGB2BGR))

        return superimposed
    
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

