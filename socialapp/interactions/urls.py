from django.urls import path, include
from .views import FeedView, RemoveFollowerAPIView, SearchUserAPIView,FollowUserAPIView, SuggestionAPIView,UnfollowUserAPIView,ListUserConnectionsAPIView

urlpatterns = [
    path('search-users/', SearchUserAPIView.as_view(), name='search-users'),
    path('follow/<int:user_id>/', FollowUserAPIView.as_view(), name='follow_user'),
    path('unfollow/<int:user_id>/', UnfollowUserAPIView.as_view(), name='unfollow_user'),
    path('remove-follower/<int:user_id>/', RemoveFollowerAPIView.as_view(), name='remove-follower'),
    path('connections/', ListUserConnectionsAPIView.as_view(), name='connections'),
    path('suggestions/', SuggestionAPIView.as_view(), name='suggestions'),
    path('feed/', FeedView.as_view(), name='feeds'),
]
