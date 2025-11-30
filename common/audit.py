from __future__ import annotations

import json
from typing import Any, Dict, Optional, TypeVar

from django.apps import apps
from django.contrib.auth import get_user_model
from rest_framework import serializers

from common.typing import (
    ModelLike,
    RequestWithUser,
    RoleAwareUser,
    SerializerProtocol,
)


TModel = TypeVar("TModel", bound=ModelLike)


class AuditLoggingMixin:
    """
    Переиспользуемый mixin для ViewSets для логирования операций CREATE/UPDATE/DELETE в AuditLog.
    """

    audit_serializer_class: Optional[type[serializers.ModelSerializer[Any]]] = None
    request: RequestWithUser

    def _get_current_user(self) -> Optional[RoleAwareUser]:
        user = getattr(self.request, "user", None)
        return user if user and user.is_authenticated else None

    def _serialize_instance(self, instance: ModelLike) -> Dict[str, Any]:
        serializer_class = self.audit_serializer_class or self.get_serializer_class()
        serializer = serializer_class(
            instance,
            context={"request": getattr(self, "request", None)},
        )
        return serializer.data

    def _create_audit_log(
        self,
        *,
        instance: ModelLike,
        action_type: str,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
    ) -> None:
        AuditLog = apps.get_model("reports", "AuditLog")  # noqa: N806
        AuditLog.objects.create(
            user=self._get_current_user(),
            action_type=action_type,
            table_name=instance._meta.db_table,
            record_id=getattr(instance, "pk", 0) or 0,
            old_values=json.dumps(old_values, ensure_ascii=False) if old_values else None,
            new_values=json.dumps(new_values, ensure_ascii=False) if new_values else None,
        )

    def save_and_log_create(
        self,
        serializer: SerializerProtocol[TModel],
        **save_kwargs: Any,
    ) -> TModel:
        instance = serializer.save(**save_kwargs)
        self._create_audit_log(
            instance=instance,
            action_type="CREATE",
            new_values=self._serialize_instance(instance),
        )
        return instance

    def update_and_log(
        self,
        serializer: SerializerProtocol[TModel],
        **save_kwargs: Any,
    ) -> TModel:
        instance_before = serializer.instance
        old_values = self._serialize_instance(instance_before)
        instance_after = serializer.save(**save_kwargs)
        self._create_audit_log(
            instance=instance_after,
            action_type="UPDATE",
            old_values=old_values,
            new_values=self._serialize_instance(instance_after),
        )
        return instance_after

    def delete_and_log(self, instance: ModelLike) -> None:
        old_values = self._serialize_instance(instance)
        self._create_audit_log(
            instance=instance,
            action_type="DELETE",
            old_values=old_values,
        )
        instance.delete()

    def perform_create(self, serializer: serializers.ModelSerializer) -> None:  # type: ignore[override]
        self.save_and_log_create(serializer)

    def perform_update(self, serializer: serializers.ModelSerializer) -> None:  # type: ignore[override]
        self.update_and_log(serializer)

    def perform_destroy(self, instance: Any) -> None:  # type: ignore[override]
        self.delete_and_log(instance)

