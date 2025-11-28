from rest_framework import serializers
from .models import Greenhouse, Section

class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = '__all__'

class GreenhouseSerializer(serializers.ModelSerializer):
    sections = SectionSerializer(many=True, read_only=True) # Вложенный список секций

    class Meta:
        model = Greenhouse
        fields = '__all__'