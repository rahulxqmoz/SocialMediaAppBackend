from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

class TokenValidationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Extract token from the Authorization header
        token = request.headers.get('Authorization', '').split(' ')[-1]

        # Validate the token
        try:
            if token:
                JWTAuthentication().get_validated_token(token)
        except (InvalidToken, TokenError) as e:
            print(f"Token validation error in middleware: {e}")

        response = self.get_response(request)
        return response
