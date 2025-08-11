from abc import ABC, abstractmethod

class BasePermissionPlugin(ABC):
    @abstractmethod
    def has_permission(self, request, context: dict) -> bool:
        """
        Decide if write is allowed based on the request and target_object.
        Should extract claims or other auth info from request.user.
        """
        pass
