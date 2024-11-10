import jwt
from core.models import User
from django.http import HttpResponseForbidden
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from asgiref.sync import sync_to_async
from jwt.exceptions import ExpiredSignatureError
import logging

logger = logging.getLogger(__name__)

class AuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'websocket' and scope['path'].startswith('/ws/'):
            token = self.extract_token(scope['path'])

            if not token:
                logger.warning("No token provided in WebSocket connection.")
                await send({
                    'type': 'websocket.close',
                    'code': 400,  # Bad request
                })
                return

            logger.debug(f"Received token: {token}")

            auth = JWTAuthentication()
            try:
                validated_token = auth.get_validated_token(token)
                user_id = validated_token['user_id']

                user = await sync_to_async(User.objects.get)(id=user_id)
                scope['user'] = user
                logger.info(f"User authenticated: {user}")

            except (InvalidToken, TokenError, User.DoesNotExist, ExpiredSignatureError) as e:
                logger.error(f"Authentication failed: {str(e)}")
                await send({
                    'type': 'websocket.close',
                    'code': 403,  # Forbidden
                })
                return

        return await self.inner(scope, receive, send)

    def extract_token(self, path):
        parts = path.strip('/').split('/')
        if len(parts) > 1:
            return parts[-1]
        return None
