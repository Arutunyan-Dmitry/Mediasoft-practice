from rest_framework import permissions


class CurrentNonAdminUserOnly(permissions.IsAuthenticated):
    """
    Доступ только текущему пользователю, но не администратору
    """
    def has_permission(self, request, view):
        return bool(not request.user.is_staff and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        return not user.is_staff and obj.pk == user.pk
