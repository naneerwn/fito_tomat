from __future__ import annotations

"""
Общие вспомогательные типы для структурной (утинной) типизации.

Бэкенд часто опирается на неявно передаваемые объекты Django/DRF. Этот
модуль описывает небольшие ``Protocol``-классы, чтобы зафиксировать
ожидания от поведения без привязки к конкретным моделям или
сериализаторам.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Protocol, Sequence, TypeVar, runtime_checkable

TModel = TypeVar("TModel")


@runtime_checkable
class RoleLike(Protocol):
    """Сущность, у которой есть атрибут ``name`` (роль, группа и т.п.)."""

    name: str


@runtime_checkable
class RoleAwareUser(Protocol):
    """
    Минимальный интерфейс пользователя, участвующего в проверках прав.
    """

    id: Any
    is_authenticated: bool
    is_staff: bool
    role: RoleLike | None


@runtime_checkable
class RequestWithUser(Protocol):
    """DRF-запрос или его аналог с атрибутом ``user``."""

    user: RoleAwareUser | None


@runtime_checkable
class ModelLike(Protocol):
    """Экземпляр модели Django, описанный утиным способом."""

    pk: Any
    _meta: Any

    def delete(self) -> Any: ...


@runtime_checkable
class SerializerProtocol(Protocol[TModel]):
    """
    Часть API ``ModelSerializer`` из DRF, используемая в модулях.

    Сериализатор описывается структурно, поэтому любая совместимая
    реализация с методами ``save()``, ``data`` и ``instance`` будет
    приниматься типами.
    """

    instance: TModel
    data: Mapping[str, Any]
    context: Mapping[str, Any] | None

    def save(self, **kwargs: Any) -> TModel: ...


@runtime_checkable
class Timestamped(Protocol):
    """Объект с атрибутами ``created_at``/``updated_at``."""

    created_at: datetime
    updated_at: datetime | None


@runtime_checkable
class DateTimeLike(Protocol):
    """Минимальный набор поведения ``datetime``, необходимый отчётам."""

    tzinfo: Any

    def isoformat(self) -> str: ...


@dataclass(slots=True)
class RoleCheckContext:
    """
    Вспомогательная структура для проверок ролей.

    Явное хранение пользователя и целевых ролей упрощает код, сохраняя
    при этом утиный подход.
    """

    user: RoleAwareUser
    target_roles: Sequence[str]

    def matches(self) -> bool:
        role = getattr(self.user, "role", None)
        role_name = getattr(role, "name", None) if role else None
        return bool(self.user.is_staff or role_name in self.target_roles)

