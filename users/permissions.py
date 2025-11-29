from typing import Sequence

from rest_framework.permissions import BasePermission, SAFE_METHODS

from common.typing import RequestWithUser, RoleAwareUser, RoleCheckContext


def _has_role(user: RoleAwareUser, roles: Sequence[str]) -> bool:
    return RoleCheckContext(user=user, target_roles=roles).matches()


class IsAgronomistOrAdmin(BasePermission):
    """
    Read for everyone, write only for агрономов или админов.
    """

    def has_permission(self, request: RequestWithUser, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return _has_role(request.user, ['Агроном', 'Администратор'])


class IsOperator(BasePermission):
    def has_permission(self, request: RequestWithUser, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        return _has_role(request.user, ['Оператор'])


class IsAdminOrAgronomistOnly(BasePermission):
    """
    CRUD доступ только администраторам или агрономам (без исключений по методам).
    """

    def has_permission(self, request: RequestWithUser, view) -> bool:
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False
        return _has_role(user, ['Агроном', 'Администратор'])

