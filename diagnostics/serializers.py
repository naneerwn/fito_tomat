from rest_framework import serializers
from .models import Disease, Treatment, Image, Diagnosis


class DiseaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Disease
        fields = '__all__'


class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = '__all__'
        read_only_fields = ('user', 'uploaded_at',)  # Пользователь проставляется автоматически
        ordering = ['-timestamp']


class DiagnosisSerializer(serializers.ModelSerializer):
    disease_name = serializers.CharField(source='disease.name', read_only=True)
    heatmap_url = serializers.SerializerMethodField()

    class Meta:
        model = Diagnosis
        fields = '__all__'

    def get_heatmap_url(self, obj):
        """Возвращает URL для доступа к тепловой карте."""
        if obj.heatmap_path:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.heatmap_path.url)
            return obj.heatmap_path.url
        return None