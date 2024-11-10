from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    receiver_username = serializers.CharField(source='receiver.username', read_only=True)
    sender_profile_pic = serializers.ImageField(source='sender.profile_pic', read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'sender', 'sender_username', 'receiver', 'receiver_username', 'notification_type', 'post', 'comment', 'follow', 'created_at', 'is_read','sender_profile_pic','announcement_content']
        read_only_fields = ['sender', 'receiver', 'created_at']
    