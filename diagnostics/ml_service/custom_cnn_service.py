"""
ML Service для диагностики заболеваний томатов с использованием Custom CNN.
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
IMG_SIZE = 256  # Custom CNN использует 256x256
NORMALIZE_MEAN = (0.485, 0.456, 0.406)
NORMALIZE_STD = (0.229, 0.224, 0.225)
NUM_CLASSES = len(DISEASE_CLASSES)


class Mish(nn.Module):
    """Mish activation function из кода обучения."""
    def forward(self, x):
        return x * torch.tanh(F.softplus(x))


class SEBlock(nn.Module):
    """Squeeze-and-Excitation блок из кода обучения."""
    def __init__(self, in_channels, reduction=16):
        super().__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Sequential(
            nn.Linear(in_channels, in_channels // reduction, bias=False),
            Mish(),
            nn.Linear(in_channels // reduction, in_channels, bias=False),
            nn.Sigmoid()
        )
    
    def forward(self, x):
        b, c, _, _ = x.size()
        y = self.avg_pool(x).view(b, c)
        y = self.fc(y).view(b, c, 1, 1)
        return x * y


class ResBlockMish(nn.Module):
    """Residual блок с Mish activation из кода обучения."""
    def __init__(self, in_ch, out_ch, stride=1, dropout=0.0):
        super().__init__()
        self.conv1 = nn.Conv2d(in_ch, out_ch, 3, stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(out_ch)
        self.conv2 = nn.Conv2d(out_ch, out_ch, 3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(out_ch)
        self.se = SEBlock(out_ch)
        self.act = Mish()
        self.drop = nn.Dropout2d(dropout) if dropout > 0 else nn.Identity()
        self.shortcut = nn.Sequential()
        if stride != 1 or in_ch != out_ch:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_ch, out_ch, 1, stride=stride, bias=False),
                nn.BatchNorm2d(out_ch)
            )
    
    def forward(self, x):
        out = self.act(self.bn1(self.conv1(x)))
        out = self.drop(out)
        out = self.bn2(self.conv2(out))
        out = self.se(out)
        out += self.shortcut(x)
        out = self.act(out)
        return out


class TomatoNet(nn.Module):
    """Архитектура Custom CNN (TomatoNet) из кода обучения."""
    
    def __init__(self, num_classes: int):
        super().__init__()
        self.stem = nn.Sequential(
            nn.Conv2d(3, 64, 7, stride=2, padding=3, bias=False),
            nn.BatchNorm2d(64), 
            Mish(), 
            nn.MaxPool2d(3, stride=2, padding=1)
        )
        self.layer1 = self._make_layer(64, 64, 2, 1)
        self.layer2 = self._make_layer(64, 128, 2, 2)
        self.layer3 = self._make_layer(128, 256, 2, 2)
        self.layer4 = self._make_layer(256, 512, 2, 2)
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.flatten = nn.Flatten()
        self.drop = nn.Dropout(0.4)
        self.fc = nn.Linear(512, num_classes)
        
        # Инициализация весов
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, (nn.BatchNorm2d, nn.GroupNorm)):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
    
    def _make_layer(self, in_ch, out_ch, blocks, stride):
        layers = [ResBlockMish(in_ch, out_ch, stride)]
        for _ in range(1, blocks):
            layers.append(ResBlockMish(out_ch, out_ch))
        return nn.Sequential(*layers)
    
    def forward(self, x):
        x = self.stem(x)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        x = self.pool(x)
        x = self.flatten(x)
        x = self.drop(x)
        return self.fc(x)


class CustomCNNPredictor:
    """Сервис для предсказания заболеваний томатов с использованием Custom CNN."""

    def __init__(self, model_path: Optional[str] = None):
        """
        Инициализация сервиса.

        Параметры:
            model_path: Путь к файлу модели .pth. Если None, используется путь из settings.
        """
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.model_path = model_path or getattr(settings, 'CUSTOM_CNN_MODEL_PATH', None)
        
        if not self.model_path:
            # Путь по умолчанию
            base_dir = Path(settings.BASE_DIR)
            self.model_path = str(base_dir / 'models' / 'best_model.pth')
        
        self._load_model()

    def _load_model(self) -> None:
        """Загрузка обученной модели."""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Модель не найдена: {self.model_path}")
        
        # Создаем модель с той же архитектурой
        self.model = TomatoNet(NUM_CLASSES)
        
        # Загружаем веса
        state_dict = torch.load(self.model_path, map_location=self.device)
        self.model.load_state_dict(state_dict)
        self.model.to(self.device)
        self.model.eval()
        
        print(f"Custom CNN модель загружена: {self.model_path}")

    def preprocess_image(self, image_path: str) -> torch.Tensor:
        """
        Предобработка изображения для инференса.

        Параметры:
            image_path: Путь к изображению.

        Возвращает:
            Тензор изображения [1, 3, 256, 256].
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
        orig_h, orig_w = orig_img.shape[:2]
        
        # Подготавливаем тензор с requires_grad=True для вычисления градиентов
        img_tensor = self.preprocess_image(image_path)
        img_tensor.requires_grad_(True)
        
        # Регистрируем хуки для перехвата градиентов и активаций
        gradients = []
        activations = []
        
        def backward_hook(module, grad_input, grad_output):
            if grad_output[0] is not None:
                gradients.append(grad_output[0].detach())
        
        def forward_hook(module, input, output):
            activations.append(output.detach())
        
        # Подключаемся к последнему сверточному слою перед pooling
        # В TomatoNet это последний блок layer4, берем последний Conv2d из него
        target_layer = None
        last_block = self.model.layer4[-1] if hasattr(self.model.layer4, '__getitem__') else self.model.layer4
        if last_block is not None:
            # Ищем последний Conv2d в последнем блоке
            for module in reversed(list(last_block.modules())):
                if isinstance(module, nn.Conv2d):
                    target_layer = module
                    break
        
        # Если не нашли в layer4, ищем в любой части модели
        if target_layer is None:
            for module in reversed(list(self.model.modules())):
                if isinstance(module, nn.Conv2d):
                    target_layer = module
                    break
        
        if target_layer is None:
            raise ValueError("Не удалось найти подходящий сверточный слой для GRAD-CAM")
        
        handle_b = target_layer.register_full_backward_hook(backward_hook)
        handle_f = target_layer.register_forward_hook(forward_hook)
        
        try:
            # Прямой проход
            self.model.eval()
            output = self.model(img_tensor)
            pred_idx = output.argmax(dim=1).item()
            
            # Обратный проход
            self.model.zero_grad()
            # Используем logits для правильного вычисления градиентов
            score = output[0, pred_idx]
            score.backward()
            
            # Проверяем, что градиенты получены
            if len(gradients) == 0 or len(activations) == 0:
                raise ValueError("Не удалось получить градиенты или активации")
            
            # Вычисляем веса
            grads = gradients[0].cpu().numpy()[0]  # [Каналы, H, W]
            fmaps = activations[0].cpu().numpy()[0]  # [Каналы, H, W]
            
            # Проверяем размеры
            if len(grads.shape) != 3 or len(fmaps.shape) != 3:
                raise ValueError(f"Неожиданная форма градиентов или активаций: grads={grads.shape}, fmaps={fmaps.shape}")
            
            # Глобальное усреднение градиентов (Global Average Pooling)
            # Усредняем по пространственным измерениям (H, W)
            weights = np.mean(grads, axis=(1, 2))  # [Каналы]
            
            # Строим CAM: взвешенная сумма feature maps
            cam = np.zeros(fmaps.shape[1:], dtype=np.float32)  # [H, W]
            for i, w in enumerate(weights):
                cam += w * fmaps[i]
            
            # Применение ReLU (убираем отрицательные значения)
            cam = np.maximum(cam, 0)
            
            # Нормализация к [0, 1]
            cam = cam - np.min(cam)
            if np.max(cam) > 0:
                cam = cam / np.max(cam)
            
            # Изменяем размер до оригинального размера изображения
            cam_resized = cv2.resize(cam, (orig_w, orig_h))
            
            # Применяем цветовую карту
            heatmap_colored = cv2.applyColorMap(
                np.uint8(255 * cam_resized),
                cv2.COLORMAP_JET
            )
            heatmap_colored = cv2.cvtColor(heatmap_colored, cv2.COLOR_BGR2RGB)
            
            # Наложение на оригинал (используем оригинальный размер)
            superimposed = np.uint8(0.6 * orig_img + 0.4 * heatmap_colored)
            
            # Сохраняем, если указан путь
            if output_path:
                cv2.imwrite(output_path, cv2.cvtColor(superimposed, cv2.COLOR_RGB2BGR))
            
            return superimposed
            
        finally:
            # Удаляем хуки
            handle_b.remove()
            handle_f.remove()
            # Отключаем requires_grad
            img_tensor.requires_grad_(False)


# Глобальный экземпляр сервиса (singleton)
_custom_cnn_instance: Optional[CustomCNNPredictor] = None


def get_custom_cnn_predictor() -> CustomCNNPredictor:
    """Получить экземпляр сервиса (singleton pattern)."""
    global _custom_cnn_instance
    if _custom_cnn_instance is None:
        _custom_cnn_instance = CustomCNNPredictor()
    return _custom_cnn_instance

