from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Disease, Image, Diagnosis
from .serializers import DiseaseSerializer, ImageSerializer, DiagnosisSerializer
from common.audit import AuditLoggingMixin
from users.permissions import IsAgronomistOrAdmin
from .ml_service.diagnosis_service import run_ml_diagnosis

class DiseaseViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = Disease.objects.all()
    serializer_class = DiseaseSerializer
    permission_classes = [IsAgronomistOrAdmin]
    # Справочник болезней: читать могут все, менять - Агроном/Админ (упростим до IsAuthenticated для чтения)

class ImageViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = Image.objects.all()
    serializer_class = ImageSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        # Автоматически привязываем загрузившего пользователя
        image_instance = self.save_and_log_create(serializer, user=self.request.user)
        
        # Запускаем ML-диагностику автоматически
        try:
            run_ml_diagnosis(image_instance)
        except Exception as e:
            # Логируем ошибку, но не прерываем создание изображения
            print(f"⚠️ Ошибка при автоматической диагностике: {e}")

    def get_queryset(self):
        user = self.request.user
        # Оператор видит только свои, Агроном/Админ - все
        if user.role and user.role.name in ['Агроном', 'Администратор']:
            return Image.objects.all()
        return Image.objects.filter(user=user)

class DiagnosisViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = Diagnosis.objects.all()
    serializer_class = DiagnosisSerializer
    permission_classes = [IsAgronomistOrAdmin]
    # Здесь в будущем добавим логику подтверждения диагноза агрономом