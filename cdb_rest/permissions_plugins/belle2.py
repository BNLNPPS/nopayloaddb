from .base import BasePermissionPlugin
import re

class Belle2PermissionPlugin(BasePermissionPlugin):
    def has_permission(self, request, context: dict) -> bool:
        match_found = False
        claims = getattr(request.user, "claims", {})
        #allowed_objects = claims.get("allowed_objects", [])
        if context.get("object") in ("GlobalTag"):
            name = context.get("name", "")
            role = context.get("role", "")
            patterns = claims.get('b2cdb:admin', []) #createpayload, createiov
            match_found = any(re.fullmatch(pattern, name) for pattern in patterns)
            if role == "createiov":
                patterns = claims.get('b2cdb:createiov', [])
                match_found = match_found or any(re.fullmatch(pattern, name) for pattern in claims.get('b2cdb:createiov', []))

            if match_found:
                return True
            
        if context.get("object") in ("PayloadList"):
            name = context.get("name", "")
            role = context.get("role", "")
            if role == "createpayload":
                patterns = claims.get('b2cdb:createpayload', [])
                match_found = any(re.fullmatch(pattern, name) for pattern in patterns)

                if match_found:
                    return True
            
                   
            return False
