# consumer.py
import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from  .models import Follow
from  posts.models import Post
from .serializers import PostSerializer

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.channel_layer.group_add(
            'notifications',  # Use the same group name as in notify_user_followed
            self.channel_name
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            'notifications',
            self.channel_name
        )

    async def send_notification(self, event):
        await self.send(text_data=event['notification'])

class FeedConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        self.group_name = 'feed'
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.close()

    async def receive(self, text_data):
        pass

    async def send_feed_update(self, event):
        post = Post.objects.get(id=event['post_id'])
        serializer = PostSerializer(post)
        await self.send(text_data=json.dumps(serializer.data))

    async def fetch_newer_posts(self, event):
        user = self.scope['user']
        following_ids = [follow.following.id for follow in Follow.objects.filter(follower=user)]
        following_ids.append(user.id)  # Include the user's own posts

        # Get newer posts from users the current user is following
        newer_posts = Post.objects.filter(user_id__in=following_ids, created_at__gt=event['last_post_time']).order_by('-created_at')

        serializer = PostSerializer(newer_posts, many=True)
        await self.send(text_data=json.dumps(serializer.data))