"""
ML Service для диагностики заболеваний томатов с использованием YOLO.
Включает детекцию объектов (bounding boxes) и классификацию через детекцию.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple, Optional, List, Dict, Any

import cv2
import numpy as np
import torch

from django.conf import settings

try:
    from ultralytics import YOLO
except ImportError:
    raise ImportError(
        "ultralytics не установлен. Установите: pip install ultralytics"
    )

# Классы заболеваний (соответствуют порядку обучения модели)
# Порядок должен совпадать с другими моделями (sorted order)
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
IMG_SIZE = 224  # YOLO classification использует 224x224
CONF_THRESHOLD = 0.25
IOU_THRESHOLD = 0.45
NUM_CLASSES = len(DISEASE_CLASSES)


class YOLOPredictor:
    """Сервис для предсказания заболеваний томатов с использованием YOLO."""

    def __init__(self, model_path: Optional[str] = None):
        """
        Инициализация сервиса.

        Параметры:
            model_path: Путь к файлу модели .pt. Если None, используется путь из settings.
        """
        self.model = None
        self.model_path = model_path or getattr(settings, 'YOLO_MODEL_PATH', None)
        
        if not self.model_path:
            # Путь по умолчанию
            base_dir = Path(settings.BASE_DIR)
            self.model_path = str(base_dir / 'models' / 'best.pt')
        
        self._load_model()

    def _load_model(self) -> None:
        """Загрузка обученной модели."""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Модель не найдена: {self.model_path}")
        
        # Загружаем YOLO модель
        self.model = YOLO(self.model_path)
        # Не вызываем fuse() для Grad-CAM: fused SiLU с inplace ломает autograd hooks
        # self.model.fuse()
        # Отключаем inplace у SiLU, чтобы избежать ошибок вида "view is modified inplace"
        model_for_cam = getattr(self.model, 'model', self.model)
        for module in model_for_cam.modules():
            if isinstance(module, torch.nn.SiLU) and getattr(module, 'inplace', False):
                module.inplace = False
        # Имена классов: используем то, что в модели, но если размер не совпадает — fallback на DISEASE_CLASSES
        model_names = getattr(self.model, 'names', None)
        if isinstance(model_names, dict) and len(model_names) == NUM_CLASSES:
            self.names_map = {int(k): str(v) for k, v in model_names.items()}
        else:
            if model_names:
                print(f"⚠️ Несоответствие числа классов: в модели {len(model_names)}, ожидалось {NUM_CLASSES}. Используем DISEASE_CLASSES.")
            self.names_map = {i: cls for i, cls in enumerate(DISEASE_CLASSES)}
        
        print(f"YOLO модель загружена: {self.model_path}")

    def predict(self, image_path: str) -> Tuple[str, float, np.ndarray]:
        """
        Предсказание заболевания на изображении через YOLO classification.
        YOLO11 classification возвращает вероятности классов напрямую.

        Параметры:
            image_path: Путь к изображению.

        Возвращает:
            Tuple (название_заболевания, confidence, вероятности_всех_классов).
        """
        # Предсказание с YOLO (classification mode)
        results = self.model.predict(
            image_path,
            imgsz=IMG_SIZE,
            verbose=False,
        )
        
        if len(results) == 0:
            # Если ничего не получено, возвращаем класс по умолчанию
            disease_name = DISEASE_CLASSES[0]
            confidence = 0.0
            probs = np.zeros(NUM_CLASSES)
            probs[0] = 1.0
            return disease_name, confidence, probs
        
        # Для YOLO classification используем probs
        result = results[0]
        if hasattr(result, 'probs') and result.probs is not None:
            # Получаем вероятности классов
            probs_tensor = result.probs.data
            probs = probs_tensor.cpu().numpy()
            
            # Находим класс с максимальной вероятностью
            pred_idx = int(probs.argmax())
            confidence = float(probs[pred_idx])
            
            # Нормализуем вероятности (на всякий случай)
            probs_sum = probs.sum()
            if probs_sum > 0:
                probs = probs / probs_sum
            
            # Получаем название класса
            names_map = getattr(self, 'names_map', None)
            if names_map and pred_idx in names_map:
                disease_name = names_map[pred_idx]
            else:
                disease_name = IDX_TO_CLASS.get(pred_idx, DISEASE_CLASSES[0])
            
            return disease_name, confidence, probs
        else:
            # Fallback: если probs недоступны
            disease_name = DISEASE_CLASSES[0]
            confidence = 0.0
            probs = np.zeros(NUM_CLASSES)
            probs[0] = 1.0
            return disease_name, confidence, probs

    def detect(self, image_path: str) -> List[Dict[str, Any]]:
        """
        Детекция объектов на изображении (для YOLO classification возвращает класс с максимальной вероятностью).

        Параметры:
            image_path: Путь к изображению.

        Возвращает:
            Список словарей с детекциями (для classification - один элемент с классом):
            [{
                'class': int,
                'class_name': str,
                'confidence': float,
                'bbox': [x1, y1, x2, y2],  # Для classification - весь кадр
            }, ...]
        """
        results = self.model.predict(
            image_path,
            imgsz=IMG_SIZE,
            verbose=False,
        )
        
        detections = []
        names_map = getattr(self, 'names_map', None)
        def idx_to_name(idx: int) -> str:
            if names_map and idx in names_map:
                return names_map[idx]
            return IDX_TO_CLASS.get(idx, str(idx))
        
        if len(results) > 0:
            result = results[0]
            # Для YOLO classification используем probs
            if hasattr(result, 'probs') and result.probs is not None:
                probs = result.probs.data.cpu().numpy()
                pred_idx = int(probs.argmax())
                confidence = float(probs[pred_idx])
                
                # Для classification возвращаем весь кадр как bbox
                # Загружаем изображение для получения размеров
                orig_img = cv2.imread(image_path)
                if orig_img is not None:
                    h, w = orig_img.shape[:2]
                    detections.append({
                        'class': pred_idx,
                        'class_name': idx_to_name(pred_idx),
                        'confidence': confidence,
                        'bbox': [0.0, 0.0, float(w), float(h)],
                    })
        
        return detections

    def generate_gradcam(
        self,
        image_path: str,
        output_path: Optional[str] = None,
    ) -> np.ndarray:
        """
        Генерация тепловой карты через настоящий GRAD-CAM для YOLO-классификатора.
        Используем последний сверточный слой модели, хуки для активаций и градиентов.
        """
        # Загружаем оригинальное изображение
        orig_img = cv2.imread(image_path)
        if orig_img is None:
            raise ValueError(f"Не удалось загрузить изображение: {image_path}")
        orig_img = cv2.cvtColor(orig_img, cv2.COLOR_BGR2RGB)
        orig_h, orig_w = orig_img.shape[:2]

        # Подготовка тензора (как в inference YOLO cls: RGB, 0..1, resize 224)
        img_resized = cv2.resize(orig_img, (IMG_SIZE, IMG_SIZE))
        img_tensor = torch.from_numpy(img_resized).permute(2, 0, 1).float() / 255.0  # [3, H, W]
        img_tensor = img_tensor.unsqueeze(0)  # [1, 3, H, W]
        img_tensor.requires_grad_(True)

        # Определяем устройство модели
        model_for_cam = getattr(self.model, 'model', self.model)
        device = next(model_for_cam.parameters()).device
        img_tensor = img_tensor.to(device)

        # Находим последний сверточный слой
        target_layer = None
        for module in reversed(list(model_for_cam.modules())):
            if isinstance(module, torch.nn.Conv2d):
                target_layer = module
                break
        if target_layer is None:
            raise ValueError("Не удалось найти сверточный слой для GRAD-CAM в YOLO модели")

        gradients: List[torch.Tensor] = []
        activations: List[torch.Tensor] = []

        def forward_hook(module, inp, out):
            activations.append(out.detach())

        def backward_hook(module, grad_in, grad_out):
            if grad_out[0] is not None:
                gradients.append(grad_out[0].detach())

        handle_f = target_layer.register_forward_hook(forward_hook)
        handle_b = target_layer.register_full_backward_hook(backward_hook)

        try:
            model_for_cam.eval()
            output = model_for_cam(img_tensor)
            # Ultralytics forward может вернуть tuple; берем первый элемент как logits
            if isinstance(output, (list, tuple)):
                output = output[0]
            pred_idx = int(output.argmax(dim=1).item())

            model_for_cam.zero_grad()
            score = output[0, pred_idx]
            score.backward()

            if len(gradients) == 0 or len(activations) == 0:
                raise ValueError("Не удалось получить градиенты или активации для GRAD-CAM")

            grads = gradients[0].cpu().numpy()[0]  # [C, h, w]
            fmaps = activations[0].cpu().numpy()[0]  # [C, h, w]

            weights = np.mean(grads, axis=(1, 2))  # [C]
            cam = np.zeros(fmaps.shape[1:], dtype=np.float32)
            for i, w in enumerate(weights):
                cam += w * fmaps[i]

            cam = np.maximum(cam, 0)
            cam = cam - cam.min()
            if cam.max() > 0:
                cam = cam / cam.max()

            cam_resized = cv2.resize(cam, (orig_w, orig_h))
            heatmap = cv2.applyColorMap(np.uint8(255 * cam_resized), cv2.COLORMAP_JET)
            heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)

            superimposed = np.uint8(0.6 * orig_img + 0.4 * heatmap)

            if output_path:
                cv2.imwrite(output_path, cv2.cvtColor(superimposed, cv2.COLOR_RGB2BGR))

            return superimposed
        finally:
            handle_f.remove()
            handle_b.remove()
            img_tensor.requires_grad_(False)


# Глобальный экземпляр сервиса (singleton)
_yolo_instance: Optional[YOLOPredictor] = None


def get_yolo_predictor() -> YOLOPredictor:
    """Получить экземпляр сервиса (singleton pattern)."""
    global _yolo_instance
    if _yolo_instance is None:
        _yolo_instance = YOLOPredictor()
    return _yolo_instance

