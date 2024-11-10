from django.db import models
from core.models import User

# Create your models here.
class Follow(models.Model):
    follower = models.ForeignKey(User, related_name='followers', on_delete=models.CASCADE)
    following = models.ForeignKey(User, related_name='following', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')  # Ensure unique following relationship

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"
