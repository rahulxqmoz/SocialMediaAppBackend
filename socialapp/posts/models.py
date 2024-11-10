from django.db import models
from core.models import User

# Create your models here.
class Post(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField(blank=True, null=True)  # For writings with emojis
    image = models.ImageField(upload_to='post_images/', null=True, blank=True)  # For images
    video = models.FileField(upload_to='post_videos/', null=True, blank=True)  # For videos
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # New fields for reporting and moderation
    is_reported = models.BooleanField(default=False)  # Whether the post has been reported
    is_approved = models.BooleanField(default=True)  # Whether the post is approved by admin
    report_reason = models.CharField(max_length=255, blank=True, null=True)  # Reason for reporting
    reported_by = models.ManyToManyField(User, related_name='reported_posts', blank=True)  # Users who reported this post

    def __str__(self):
        return f"Post by {self.user.username} on {self.created_at}"
    
    def total_likes(self):
        return self.likes.count()

    def total_comments(self):
        return Comment.objects.filter(post=self).count()

class Report(models.Model):
    REASON_CHOICES = [
        ('SPAM', 'Spam'),
        ('HATE', 'Hate Speech'),
        ('NUDITY', 'Nudity'),
        ('VIOLENCE', 'Violence'),
        ('OTHER', 'Other'),
    ]

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reports')
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports')
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    additional_info = models.TextField(blank=True, null=True)  # Extra details for the report
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report for Post {self.post.id} by {self.reported_by.username}"


class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes')
    post = models.ForeignKey('Post', on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')  # Ensure a user can only like a post once

    def __str__(self):
        return f"{self.user.username} liked {self.post}"


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    post = models.ForeignKey('Post', on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')  # Ensure a user can only bookmark a post once

    def __str__(self):
        return f"{self.user.username} bookmarked {self.post.id}"
