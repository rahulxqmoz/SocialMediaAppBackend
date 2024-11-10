from .models import Notification
from core.models import User
def create_notification(sender, receiver, notification_type, post=None, comment=None):
    if sender != receiver:
        notification = Notification.objects.create(
            sender=sender,
            receiver=receiver,
            notification_type=notification_type,
            post=post,
            comment=comment
        )
        notification.send_websocket_notification()

def create_admin_announcement(sender, content):
    # Get all users to send the announcement to everyone
    users = User.objects.all()
    
    for user in users:
        notification = Notification.objects.create(
            sender=sender,
            receiver=user,  # Set each user as the receiver
            notification_type='announcement',
            announcement_content=content
        )
        notification.send_websocket_notification()
    
