from rest_framework import serializers
from diagnostics.models import Diagnosis
from .models import Recommendation, Task

# Допустимые статусы задачи
TASK_STATUS_CHOICES = ['Назначена', 'В работе', 'Закрыта']
TASK_STATUS_CLOSED = 'Закрыта'

class TaskSerializer(serializers.ModelSerializer):
    # План лечения из связанной рекомендации (только для чтения)
    treatment_plan = serializers.SerializerMethodField(
        help_text='План лечения из рекомендации'
    )
    
    class Meta:
        model = Task
        fields = ['id', 'recommendation', 'operator', 'description', 'status', 'deadline', 
                  'created_at', 'completed_at', 'treatment_plan']
        read_only_fields = ['treatment_plan']
    
    def get_treatment_plan(self, obj):
        """Получаем план лечения из связанной рекомендации"""
        return obj.recommendation.treatment_plan_text if obj.recommendation else None
    
    def validate_status(self, value):
        """Валидация статуса задачи"""
        if value not in TASK_STATUS_CHOICES:
            raise serializers.ValidationError(
                f'Статус должен быть одним из: {", ".join(TASK_STATUS_CHOICES)}'
            )
        return value
    
    def validate(self, attrs):
        """Валидация: нельзя изменять задачу со статусом 'Закрыта'"""
        if self.instance and self.instance.status == TASK_STATUS_CLOSED:
            raise serializers.ValidationError(
                {'status': 'Нельзя изменять задачу со статусом "Закрыта"'}
            )
        return attrs

# Специальный сериализатор для Оператора (Ограничение полей)
class OperatorTaskUpdateSerializer(serializers.ModelSerializer):
    # План лечения из связанной рекомендации (только для чтения)
    treatment_plan = serializers.SerializerMethodField(
        help_text='План лечения из рекомендации'
    )
    
    class Meta:
        model = Task
        fields = ('id', 'status', 'completed_at', 'treatment_plan', 'description', 'deadline', 'created_at', 'operator', 'recommendation') # Оператор видит все, но меняет ТОЛЬКО статус
        read_only_fields = ('id', 'treatment_plan', 'completed_at', 'description', 'deadline', 'created_at', 'operator', 'recommendation')
    
    def get_treatment_plan(self, obj):
        """Получаем план лечения из связанной рекомендации"""
        return obj.recommendation.treatment_plan_text if obj.recommendation else None
    
    def validate_status(self, value):
        """Валидация статуса задачи"""
        if value not in TASK_STATUS_CHOICES:
            raise serializers.ValidationError(
                f'Статус должен быть одним из: {", ".join(TASK_STATUS_CHOICES)}'
            )
        return value
    
    def validate(self, attrs):
        """Валидация: нельзя изменять задачу со статусом 'Закрыта'"""
        if self.instance and self.instance.status == TASK_STATUS_CLOSED:
            raise serializers.ValidationError(
                {'status': 'Нельзя изменять задачу со статусом "Закрыта"'}
            )
        
        # Автоматически устанавливаем completed_at при статусе "Закрыта"
        if attrs.get('status') == TASK_STATUS_CLOSED:
            from django.utils import timezone
            attrs['completed_at'] = timezone.now()
        
        return attrs

class RecommendationSerializer(serializers.ModelSerializer):
    # agronomist устанавливается автоматически в perform_create, не требуется в запросе
    agronomist = serializers.PrimaryKeyRelatedField(read_only=True)
    # diagnosis должен существовать в БД - используем PrimaryKeyRelatedField с queryset
    diagnosis = serializers.PrimaryKeyRelatedField(
        queryset=Diagnosis.objects.all(),
        error_messages={
            'does_not_exist': 'Диагноз с указанным ID не найден.',
            'incorrect_type': 'diagnosis должен быть числом (ID диагноза).',
        }
    )
    
    class Meta:
        model = Recommendation
        fields = '__all__'
        read_only_fields = ('agronomist', 'created_at', 'updated_at')
    
    def validate_diagnosis(self, value):
        """Дополнительная валидация диагноза"""
        if not value:
            raise serializers.ValidationError('Диагноз обязателен для создания рекомендации.')
        return value