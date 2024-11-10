from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChatRoomViewSet, MessageViewSet, get_unread_counts,initiate_call,accept_call,decline_call,end_call
router = DefaultRouter()
router.register(r'chatrooms', ChatRoomViewSet, basename='chatroom')
router.register(r'messages', MessageViewSet, basename='message')

urlpatterns = [
    path('', include(router.urls)),  # Include REST API routes
    path('messages/<str:room_name>/older/<int:oldest_message_id>/', MessageViewSet.as_view({'get': 'older_messages'})),
    path('messages/<str:room_name>/', MessageViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('messages/create-with-id/', MessageViewSet.as_view({'post': 'create_with_id'})), 
    path('messages/list-with-id/<int:room_id>/', MessageViewSet.as_view({'get': 'list_with_id'})), 
    path('unread_counts/', get_unread_counts, name='unread_counts'),
    path('chatrooms/create-group/', ChatRoomViewSet.as_view({'post': 'create_group'})),
    path('chatrooms/user-groups/', ChatRoomViewSet.as_view({'get': 'list_groups'})),
    path('chatrooms/<int:pk>/leave-group/', ChatRoomViewSet.as_view({'post': 'leave_group'})),
    path('initiate_call/', initiate_call, name='initiate_call'),
    path('accept_call/<int:call_id>/', accept_call, name='accept_call'),
    path('decline_call/<int:call_id>/', decline_call, name='decline_call'),
    path('end_call/<int:call_id>/', end_call, name='end_call'),
]
