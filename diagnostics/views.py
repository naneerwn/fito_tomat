from typing import cast

from django.db.models import QuerySet
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Disease, Image, Diagnosis
from .serializers import DiseaseSerializer, ImageSerializer, DiagnosisSerializer
from common.audit import AuditLoggingMixin
from common.typing import RoleAwareUser
from users.permissions import IsAgronomistOrAdmin
from .services import recreate_diagnosis_with_model, trigger_auto_diagnosis
from .ml_service.model_factory import MLModelType


@extend_schema(
    tags=['Диагностика'],
    description='Управление справочником заболеваний томата. Позволяет просматривать, создавать, обновлять и удалять записи о болезнях растений.'
)
class DiseaseViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    """
    ViewSet для управления заболеваниями томата.
    
    - GET /api/diseases/ - получить список всех заболеваний
    - GET /api/diseases/{id}/ - получить информацию о конкретном заболевании
    - POST /api/diseases/ - создать новое заболевание (требуется роль Агроном или Администратор)
    - PUT /api/diseases/{id}/ - обновить заболевание (требуется роль Агроном или Администратор)
    - PATCH /api/diseases/{id}/ - частично обновить заболевание (требуется роль Агроном или Администратор)
    - DELETE /api/diseases/{id}/ - удалить заболевание (требуется роль Агроном или Администратор)
    """
    queryset = Disease.objects.all()
    serializer_class = DiseaseSerializer
    permission_classes = [IsAgronomistOrAdmin]

@extend_schema(
    tags=['Диагностика'],
    description='Управление изображениями растений. При загрузке изображения автоматически запускается ML-диагностика для определения заболевания.'
)
class ImageViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    """
    ViewSet для управления изображениями растений.
    
    - GET /api/images/ - получить список изображений (операторы видят только свои, агрономы и админы - все)
    - GET /api/images/{id}/ - получить информацию о конкретном изображении
    - POST /api/images/ - загрузить новое изображение (автоматически запускается ML-диагностика)
    - PUT /api/images/{id}/ - обновить информацию об изображении
    - PATCH /api/images/{id}/ - частично обновить информацию об изображении
    - DELETE /api/images/{id}/ - удалить изображение
    
    При создании изображения автоматически запускается ML-модель для диагностики заболевания.
    """
    queryset = Image.objects.all()
    serializer_class = ImageSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer: ImageSerializer) -> None:
        # Автоматически привязываем загрузившего пользователя
        image_instance = self.save_and_log_create(serializer, user=self.request.user)
        
        # Получаем тип модели из запроса (если указан)
        model_type = serializer.validated_data.get('model_type') or None

        # Запускаем ML-диагностику автоматически (логируем внутри сервиса)
        trigger_auto_diagnosis(image_instance, model_type=model_type)

    def get_queryset(self) -> QuerySet[Image]:
        user = cast(RoleAwareUser, self.request.user)
        # Оператор видит только свои, Агроном/Админ - все
        if user.role and user.role.name in ['Агроном', 'Администратор']:
            return Image.objects.all()
        return Image.objects.filter(user=user)
    
    @extend_schema(
        tags=['Диагностика'],
        description='Получить список доступных ML-моделей для диагностики.',
        responses={200: {
            'type': 'object',
            'properties': {
                'models': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'value': {'type': 'string'},
                            'label': {'type': 'string'},
                            'description': {'type': 'string'},
                        }
                    }
                }
            }
        }}
    )
    @action(detail=False, methods=['get'], url_path='available-models')
    def available_models(self, request):
        """Получить список доступных ML-моделей."""
        models = [
            {
                'value': MLModelType.EFFNET.value,
                'label': 'EfficientNet-B3',
                'description': 'EfficientNet-B3 модель, обучена на 300x300',
            },
            {
                'value': MLModelType.CUSTOM_CNN.value,
                'label': 'Custom CNN',
                'description': 'Кастомная CNN модель (TomatoNet), обучена на 256x256',
            },
            {
                'value': MLModelType.VIT.value,
                'label': 'Vision Transformer',
                'description': 'ViT-Base модель, обучена на 224x224',
            },
            {
                'value': MLModelType.YOLO.value,
                'label': 'YOLO',
                'description': 'YOLO модель для классификации (224x224)',
            },
        ]
        return Response({'models': models})

@extend_schema(
    tags=['Диагностика'],
    description='Управление диагнозами заболеваний. Содержит результаты ML-диагностики и подтвержденные агрономом диагнозы.'
)
class DiagnosisViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    """
    ViewSet для управления диагнозами заболеваний.
    
    - GET /api/diagnoses/ - получить список всех диагнозов
    - GET /api/diagnoses/{id}/ - получить информацию о конкретном диагнозе
    - POST /api/diagnoses/ - создать новый диагноз (требуется роль Агроном или Администратор)
    - PUT /api/diagnoses/{id}/ - обновить диагноз (требуется роль Агроном или Администратор)
    - PATCH /api/diagnoses/{id}/ - частично обновить диагноз (требуется роль Агроном или Администратор)
    - DELETE /api/diagnoses/{id}/ - удалить диагноз (требуется роль Агроном или Администратор)
    - POST /api/diagnoses/{id}/recreate/ - пересоздать диагноз с другой моделью
    
    Каждый диагноз содержит информацию о ML-предсказании и подтвержденном заболевании.
    Также доступны тепловые карты (heatmaps) для визуализации областей, на которые обратила внимание модель.
    """
    queryset = Diagnosis.objects.all().order_by('-timestamp', '-id')
    serializer_class = DiagnosisSerializer
    permission_classes = [IsAgronomistOrAdmin]
    ordering = ['-timestamp', '-id']
    ordering_fields = ['timestamp', 'id']
    
    @extend_schema(
        tags=['Диагностика'],
        description='Пересоздать диагноз с использованием другой ML-модели.',
        request={
            'application/json': {
                'schema': {
                    'type': 'object',
                    'properties': {
                        'model_type': {
                            'type': 'string',
                            'enum': ['effnet', 'custom_cnn', 'vit', 'yolo'],
                            'description': 'Тип ML-модели для диагностики',
                        }
                    },
                    'required': ['model_type']
                }
            }
        },
        responses={200: DiagnosisSerializer}
    )
    @action(detail=True, methods=['post'], url_path='recreate')
    def recreate(self, request, pk=None):
        """Пересоздать диагноз с использованием другой ML-модели."""
        diagnosis = self.get_object()
        model_type = request.data.get('model_type')
        
        if not model_type:
            return Response(
                {'error': 'Не указан тип модели (model_type)'},
                status=400
            )
        
        # Удаляем старый диагноз (или можно создать новый, но удалить старый)
        # Для простоты создаем новый и удаляем старый
        image_instance = diagnosis.image

        new_diagnosis = recreate_diagnosis_with_model(diagnosis, model_type=model_type)
        serializer = self.get_serializer(new_diagnosis)
        return Response(serializer.data)