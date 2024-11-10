from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

class CustomJWTAuthentication:
    def authenticate(self, token):
        try:
            access_token = AccessToken(token)
            return access_token.payload['user_id']
        except (InvalidToken, TokenError):
            return None