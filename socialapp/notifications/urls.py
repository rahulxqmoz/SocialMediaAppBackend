

from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import AdminAnnouncementView, NotificationViewSet

router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
    path('admin/announcement/', AdminAnnouncementView.as_view(), name='admin-announcement'),
]

