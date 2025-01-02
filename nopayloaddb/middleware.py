from threading import local

# Local storage for storing the current request
_request_local = local()

def get_current_request():
    return getattr(_request_local, 'request', None)

class RequestMiddleware:
    """Middleware to store the current request for use in the DB router."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Save the request in the local thread storage
        _request_local.request = request
        response = self.get_response(request)
        # Clear the request after processing to avoid conflicts
        _request_local.request = None
        return response