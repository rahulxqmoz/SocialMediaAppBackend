from django.db import models
from .services import send_notification

from core.models import User
from django.utils import timezone
# Create your models here.

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('like', 'Like'),
        ('comment', 'Comment'),
        ('follow', 'Follow'),
        ('announcement', 'Announcement'),
    )

    sender = models.ForeignKey(User, related_name='sent_notifications', on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name='received_notifications', on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=25, choices=NOTIFICATION_TYPES)
    post = models.ForeignKey('posts.Post', related_name='notifications', null=True, blank=True, on_delete=models.CASCADE)
    comment = models.ForeignKey('posts.Comment', related_name='notifications', null=True, blank=True, on_delete=models.CASCADE)
    follow = models.ForeignKey('interactions.Follow', related_name='notifications', null=True, blank=True, on_delete=models.CASCADE)
    announcement_content = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.sender} {self.notification_type} {self.receiver}"
    
    def send_websocket_notification(self):
        # Implement sending notification to WebSocket channel
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        if self.notification_type != 'announcement':
            async_to_sync(channel_layer.group_send)(
                f"user_{self.receiver.id}",
                {
                    'type': 'send_notification',
                    'message': {
                        'sender': self.sender.username,
                        'notification_type': self.notification_type,
                        'post_id': self.post.id if self.post else None,
                        'created_at': self.created_at.isoformat()
                    }
                }
            )
        else:
        # Broadcast admin announcements to all users
            async_to_sync(channel_layer.group_send)(
                'admin_announcement',
                {
                    'type': 'send_announcement',
                    'message': {
                        'announcement': self.announcement_content,
                        'receiver' :self.receiver.id,
                        'created_at': self.created_at.isoformat()
                    }
                }
            )
    