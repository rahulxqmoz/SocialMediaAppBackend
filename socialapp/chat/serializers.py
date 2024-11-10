from rest_framework import serializers

from  core.models import User
from .models import ChatRoom, Message

class MessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.SerializerMethodField()
    sender_profile_pic = serializers.SerializerMethodField()
    class Meta:
        model = Message
        fields = ['id','sender', 'message', 'file', 'message_type', 'timestamp','read_by','sender_username', 'sender_profile_pic']

    def validate(self, data):
        # Ensure that either a message or file is provided
        if not data.get('message') and not data.get('file'):
            raise serializers.ValidationError("Message or file is required.")
        return data
    def get_sender_username(self, obj):
        return obj.sender.username

    def get_sender_profile_pic(self, obj):
        return obj.sender.profile_pic.url if obj.sender.profile_pic else None
    
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'profile_pic']

class ChatRoomSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    participants=UserSerializer(many=True, read_only=True)
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = ['id','room_name', 'participants', 'messages','is_group','group_name','unread_count']

    def get_unread_count(self, obj):
        """
        Calculate the number of unread messages in a group for the current user.
        """
        user = self.context['request'].user
        unread_messages = obj.messages.filter(sender__in=obj.participants.exclude(id=user.id)).exclude(read_by=user).count()
        return unread_messages
