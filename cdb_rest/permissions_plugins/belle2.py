from .base import BasePermissionPlugin

class Belle2PermissionPlugin(BasePermissionPlugin):
    def has_permission(self, request, context: dict) -> bool:
        claims = getattr(request.user, "claims", {})
        allowed_objects = claims.get("allowed_objects", [])
        return target_object in allowed_objects
