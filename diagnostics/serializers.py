from typing import Optional

from rest_framework import serializers
from .models import Disease, Treatment, Image, Diagnosis


class DiseaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Disease
        fields = '__all__'


class ImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    model_type = serializers.CharField(
        required=False,
        allow_blank=True,
        write_only=True,
        help_text='Тип ML-модели для диагностики: effnet, custom_cnn, vit, yolo. Если не указан, используется модель по умолчанию.',
    )

    class Meta:
        model = Image
        fields = ['id', 'section', 'user', 'file_path', 'file_format', 'camera_id', 'timestamp', 'uploaded_at', 'image_url', 'model_type']
        read_only_fields = ('user', 'uploaded_at', 'image_url')  # Пользователь проставляется автоматически
        ordering = ['-timestamp']

    def create(self, validated_data):
        # model_type используется только для выбора ML-модели, не хранится в Image
        validated_data.pop('model_type', None)
        return super().create(validated_data)

    def get_image_url(self, obj):
        """Возвращает полный URL для доступа к изображению."""
        if obj.file_path:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file_path.url)
            return obj.file_path.url
        return None


class DiagnosisSerializer(serializers.ModelSerializer):
    disease_name = serializers.CharField(source='disease.name', read_only=True)
    ml_disease_name = serializers.CharField(source='ml_disease.name', read_only=True, allow_null=True)
    is_manually_changed = serializers.SerializerMethodField()
    heatmap_url = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    model_type_display = serializers.SerializerMethodField()

    class Meta:
        model = Diagnosis
        fields = '__all__'
    
    def get_model_type_display(self, obj: Diagnosis) -> Optional[str]:
        """Возвращает читаемое название типа модели."""
        if not obj.model_type:
            return None
        
        model_names = {
            'effnet': 'EfficientNet-B3',
            'custom_cnn': 'Custom CNN (TomatoNet)',
            'vit': 'Vision Transformer',
            'yolo': 'YOLO',
        }
        return model_names.get(obj.model_type, obj.model_type)

    def get_is_manually_changed(self, obj: Diagnosis) -> bool:
        """Проверяет, был ли диагноз изменён вручную агрономом."""
        if obj.ml_disease is None:
            return False  # Если ml_disease не установлен, значит это старые записи
        return obj.ml_disease.id != obj.disease.id

    def get_heatmap_url(self, obj):
        """Возвращает URL для доступа к тепловой карте."""
        if obj.heatmap_path:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.heatmap_path.url)
            return obj.heatmap_path.url
        return None

    def get_image_url(self, obj):
        """Возвращает URL для доступа к оригинальному изображению."""
        if obj.image and obj.image.file_path:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.file_path.url)
            return obj.image.file_path.url
        return None