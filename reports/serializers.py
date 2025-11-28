import json
from rest_framework import serializers

from .models import Report, AuditLog


class ReportSerializer(serializers.ModelSerializer):
    data = serializers.SerializerMethodField(read_only=True)
    user_full_name = serializers.CharField(source='user.full_name', read_only=True)

    class Meta:
        model = Report
        fields = (
            'id',
            'user',
            'user_full_name',
            'report_type',
            'period_start',
            'period_end',
            'data',
            'generated_at',
            'file_path',
        )
        read_only_fields = ('user', 'data', 'generated_at', 'file_path')

    def get_data(self, obj):
        if not obj.data:
            return {}
        try:
            return json.loads(obj.data)
        except json.JSONDecodeError:
            return {}


class AuditLogSerializer(serializers.ModelSerializer):
    user_full_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = (
            'id',
            'user',
            'user_full_name',
            'action_type',
            'table_name',
            'record_id',
            'old_values',
            'new_values',
            'created_at',
        )
        read_only_fields = fields

    def get_user_full_name(self, obj):
        return obj.user.full_name if obj.user else None

