from rest_framework import serializers
from .models import User, Role

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source='role.name', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'full_name', 'role', 'role_name', 'is_active')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        # Хешируем пароль при создании
        user = User.objects.create_user(**validated_data)
        return user