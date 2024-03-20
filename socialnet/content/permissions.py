from rest_framework import permissions

from content.utils import is_user_in_authors_field, is_creator_or_admin, is_blog_owner


class IsCreatorOrAdmin(permissions.IsAuthenticated):
    """
    Доступ только создателю объекта или администраторам
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        return is_creator_or_admin(user, obj)


class IsBlogAuthorOrAdmin(permissions.IsAuthenticated):
    """
    Доступ только автору блога или администраторам
    """
    def has_permission(self, request, view):
        user = request.user
        return is_user_in_authors_field(request.data.get("blog_slug"), user) or user.is_staff


class IsCreatorBlogOwnerOrAdmin(permissions.IsAuthenticated):
    """
    Доступ только создателю поста, владельцу блога или администраторам
    """
    def has_object_permission(self, request, view, obj):
        user = request.user
        return is_creator_or_admin(user, obj) or is_blog_owner(user, obj.blog)

