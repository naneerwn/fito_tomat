from typing import cast

from django.db.models import QuerySet
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Disease, Image, Diagnosis
from .serializers import DiseaseSerializer, ImageSerializer, DiagnosisSerializer
from common.audit import AuditLoggingMixin
from common.typing import RoleAwareUser
from users.permissions import IsAgronomistOrAdmin
from .ml_service.diagnosis_service import run_ml_diagnosis


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
        
        # Запускаем ML-диагностику автоматически
        try:
            run_ml_diagnosis(image_instance)
        except Exception as e:
            # Логируем ошибку, но не прерываем создание изображения
            print(f"Ошибка при автоматической диагностике: {e}")

    def get_queryset(self) -> QuerySet[Image]:
        user = cast(RoleAwareUser, self.request.user)
        # Оператор видит только свои, Агроном/Админ - все
        if user.role and user.role.name in ['Агроном', 'Администратор']:
            return Image.objects.all()
        return Image.objects.filter(user=user)

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
    
    Каждый диагноз содержит информацию о ML-предсказании и подтвержденном заболевании.
    Также доступны тепловые карты (heatmaps) для визуализации областей, на которые обратила внимание модель.
    """
    queryset = Diagnosis.objects.all()
    serializer_class = DiagnosisSerializer
    permission_classes = [IsAgronomistOrAdmin]