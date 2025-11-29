from rest_framework import serializers
from .models import Disease, Treatment, Image, Diagnosis


class DiseaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Disease
        fields = '__all__'


class ImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'section', 'user', 'file_path', 'file_format', 'camera_id', 'timestamp', 'uploaded_at', 'image_url']
        read_only_fields = ('user', 'uploaded_at', 'image_url')  # Пользователь проставляется автоматически
        ordering = ['-timestamp']

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

    class Meta:
        model = Diagnosis
        fields = '__all__'

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