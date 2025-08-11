import jwt
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from django.conf import settings
from types import SimpleNamespace

class CustomJWTAuthentication(BaseAuthentication):
    """
    custom authentication class for DRF and JWT
    """

    def authenticate(self, request):
        authorization_header = request.headers.get('Authorization')
        if not authorization_header:
            raise exceptions.AuthenticationFailed('Authentication credentials were not provided')

        try:
            bearer, access_token = authorization_header.split(' ')
            if bearer != 'Bearer':
                raise exceptions.AuthenticationFailed('Wrong access_token format')

            payload = jwt.decode(
                access_token,
                settings.SECRET_KEY,
                algorithms=['HS256']
            )

        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('access_token expired')
        except jwt.InvalidSignatureError:
            raise exceptions.AuthenticationFailed('invalid signature')
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed('invalid access_token')

        # Wrap claims in a simple generic auth context object
        auth_context = SimpleNamespace(claims=payload)
        return (auth_context, None)
