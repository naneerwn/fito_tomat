"""
ML Service для диагностики заболеваний томатов.
"""

from diagnostics.ml_service.model_factory import (
    get_predictor,
    generate_heatmap,
    MLModelType,
)
from diagnostics.ml_service.ml_service import (
    DISEASE_CLASSES,
    CLASS_TO_IDX,
    IDX_TO_CLASS,
    get_predictor as get_effnet_predictor,
)
from diagnostics.ml_service.custom_cnn_service import get_custom_cnn_predictor
from diagnostics.ml_service.vit_service import get_vit_predictor
from diagnostics.ml_service.yolo_service import get_yolo_predictor

__all__ = [
    'get_predictor',
    'generate_heatmap',
    'MLModelType',
    'DISEASE_CLASSES',
    'CLASS_TO_IDX',
    'IDX_TO_CLASS',
    'get_effnet_predictor',
    'get_custom_cnn_predictor',
    'get_vit_predictor',
    'get_yolo_predictor',
]
