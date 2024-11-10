from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BookmarkViewSet, PostViewSet, ReportViewSet,CommentViewSet,LikeViewSet

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'posts', PostViewSet, basename='post')
router.register(r'reports', ReportViewSet, basename='report')
router.register(r'comments', CommentViewSet)
router.register(r'likes', LikeViewSet)
router.register(r'bookmarks', BookmarkViewSet,basename='bookmark')
# The API URLs are now determined automatically by the router.
urlpatterns = [
    path('', include(router.urls)),  # Include the router URLs under the 'api/' path
]
