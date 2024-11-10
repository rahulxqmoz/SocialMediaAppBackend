from django.db import models
from core.models import User
from channels.db import database_sync_to_async
from django.conf import settings



class ChatRoom(models.Model):
    participants = models.ManyToManyField(User, related_name='chatrooms')
    room_name = models.CharField(max_length=255, unique=True, null=True)
    group_name = models.CharField(max_length=255, unique=True, null=True, blank=True)  # For group chats
    is_group = models.BooleanField(default=False)

    def __str__(self):
        return self.group_name if self.is_group else self.room_name

class Message(models.Model):
    MESSAGE_TYPES = (
        ('text', 'Text'),
        ('image', 'Image'),
        ('gif', 'GIF'),
        ('video', 'Video'),
    )
    room = models.ForeignKey(ChatRoom, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    message = models.TextField(null=True)
    file = models.FileField(upload_to='chat_media/', null=True, blank=True)  # File field for media content
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text')
    timestamp = models.DateTimeField(auto_now_add=True)
    read_by = models.ManyToManyField(User, related_name='read_messages', blank=True) 

    class Meta:
        get_latest_by = 'timestamp'

    def __str__(self):
        return f'{self.sender} - {self.message[:20] if self.message else self.message_type}'

class CallRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('ended', 'Ended'),
        ('declined', 'Declined'),
        ('missed', 'Missed'),
    ]
    
    caller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='call_requests_sent')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='call_requests_received')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    initiated_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Call from {self.caller.username} to {self.recipient.username} - Status: {self.status}"