import jwt
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from django.conf import settings


class CustomJWTAuthentication(BaseAuthentication):
    """
    custom authentication class for DRF and JWT
    """

    def authenticate(self, request):
        try:
            authorization_header = request.headers.get('Authorization')
            if authorization_header:
                bearer, access_token = authorization_header.split(' ')
                if bearer != 'Bearer':
                    raise exceptions.AuthenticationFailed('wrong access_token format')
                payload = jwt.decode(
                    access_token, settings.SECRET_KEY, algorithms=['HS256'])
                return
            else:
                raise exceptions.AuthenticationFailed('Authentication credentials were not provided')

        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('access_token expired')
        except jwt.InvalidSignatureError:
            raise exceptions.AuthenticationFailed('invalid signature')
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed('invalid access_token')

class IndigoIAMAuthentication(BaseAuthentication):
    """
    Minimal implementation for Indigo IAM token authentication.
    """

    def authenticate(self, request):
        authorization_header = request.headers.get('Authorization')
        if not authorization_header or not authorization_header.startswith("Bearer "):
            return None  # No token provided

        token = authorization_header.split('Bearer ')[1]

        try:
            # Fetch JWKS dynamically
            jwks = requests.get(settings.IAM_JWKS_ENDPOINT).json()

            # Decode and validate token
            payload = jwt.decode(
                token,
                jwks,
                algorithms=["RS256"],
                audience=settings.IAM_AUDIENCE,
                issuer=settings.IAM_ISSUER,
            )
            return (payload, None)  # Return decoded token payload
        except JWTError:
            raise AuthenticationFailed("Invalid Indigo IAM token.")
        except requests.RequestException:
            raise AuthenticationFailed("Unable to fetch JWKS for token verification.")