from .base import BasePermissionPlugin
import re

class Belle2PermissionPlugin(BasePermissionPlugin):
    def has_permission(self, request, context: dict) -> bool:
        claims = getattr(request.user, "claims", {})
        #allowed_objects = claims.get("allowed_objects", [])
        if context.get("object") in ("GlobalTag"):
            name = context.get("name", "")
            patterns = claims.get('b2cdb:admin', [])

            match_found = any(re.fullmatch(pattern, name) for pattern in patterns)

            if match_found:
                return True
                   
            return False
