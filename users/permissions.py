from rest_framework.permissions import BasePermission, SAFE_METHODS


def _has_role(user, roles: list[str]) -> bool:
    return bool(user.is_staff or (user.role and user.role.name in roles))


class IsAgronomistOrAdmin(BasePermission):
    """
    Read for everyone, write only for агрономов или админов.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return _has_role(request.user, ['Агроном', 'Администратор'])


class IsOperator(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _has_role(request.user, ['Оператор'])


class IsAdminOrAgronomistOnly(BasePermission):
    """
    CRUD доступ только администраторам или агрономам (без исключений по методам).
    """

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False
        return _has_role(user, ['Агроном', 'Администратор'])

