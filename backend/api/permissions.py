from rest_framework.permissions import BasePermission, SAFE_METHODS


class CanAccessFarm(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role in {"admin", "extension"}:
            return request.method in SAFE_METHODS or request.user.role == "admin"
        return obj.owner_id == request.user.id


class CanManageCrop(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or request.user.role == "admin" or request.user.is_staff


class CanAccessQuestion(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role in {"admin", "extension"} or request.user.is_staff:
            return True
        return request.method in SAFE_METHODS and obj.asked_by_id == request.user.id
