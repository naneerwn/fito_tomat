from rest_framework import serializers
from .models import Recommendation, Task

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'

# Специальный сериализатор для Оператора (Ограничение полей)
class OperatorTaskUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ('id', 'status', 'completed_at') # Оператор меняет ТОЛЬКО эти поля
        read_only_fields = ('id',)

class RecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recommendation
        fields = '__all__'