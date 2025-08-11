from .base import BasePermissionPlugin

class DummyPermissionPlugin(BasePermissionPlugin):
    def has_permission(self, request, context: dict) -> bool:
        # Always allow for testing/dev
        return True
