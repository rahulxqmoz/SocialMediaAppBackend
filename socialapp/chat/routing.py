# from django.urls import re_path
# from . import consumers

# websocket_urlpatterns = [
#     re_path(r'ws/chat/(?P<room_name>[^/]+)/$', consumers.ChatConsumer.as_asgi()),
# ]
from django.urls import path
from .consumers import CallConsumer, ChatConsumer,NotificationConsumer,GroupChatConsumer,VideoCallConsumer

websocket_urlpatterns = [
    path('ws/chat/<str:room_name>/', ChatConsumer.as_asgi()),
    path('ws/unreadnotifications/<int:user_id>/', NotificationConsumer.as_asgi()),
    path('ws/groupchat/<int:room_id>/', GroupChatConsumer.as_asgi()),
    path('ws/video-call/<int:user_id>/<int:caller_id>/', VideoCallConsumer.as_asgi()),
    path('ws/call/<int:user_id>/', CallConsumer.as_asgi()),
]
