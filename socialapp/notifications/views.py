from django.shortcuts import render
from rest_framework import viewsets, permissions

from .notifications import create_admin_announcement
from .models import Notification
from .serializers import NotificationSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


# Create your views here.

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(receiver=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

class AdminAnnouncementView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, *args, **kwargs):
        content = request.data.get('content')
        if content:
            create_admin_announcement(sender=request.user, content=content)
            return Response({'status': 'Announcement sent'}, status=status.HTTP_201_CREATED)
        return Response({'error': 'Content is required'}, status=status.HTTP_400_BAD_REQUEST)