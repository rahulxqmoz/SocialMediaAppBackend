from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from notifications.notifications import create_notification
from posts.models import Post

from .models import Follow
from .serializers import PostSerializer, SearchQuerySerializer,UserSerializer
from django.db import models
from django.db.models import Q
from core.models import User
from django.shortcuts import get_object_or_404
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.db.models import Count

class SearchUserAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # Get the search query from the request parameters
        search_query = request.query_params.get('search_query', None)

        # Create a serializer instance to validate the search query
        query_serializer = SearchQuerySerializer(data={'search_query': search_query})

        if query_serializer.is_valid():
            # Fetch users based on the validated search query
            users = User.objects.filter(
                is_staff=False,
                is_suspended=False,
                is_active=True
            ).filter(
                models.Q(username__icontains=query_serializer.validated_data['search_query']) |
                models.Q(email__icontains=query_serializer.validated_data['search_query'])
            )

            # Serialize the user data
            user_serializer = UserSerializer(users, many=True)
            return Response(user_serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(query_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FollowUserAPIView(APIView):
    def post(self, request, *args, **kwargs):
        # Get the user to follow
        user_to_follow_id = kwargs.get('user_id')
        user_to_follow = get_object_or_404(User, id=user_to_follow_id)
        
        # Get the current user from the request data
        follower = get_object_or_404(User, id=request.data.get('follower_id'))

        # Create follow relationship if not exists
        follow, created = Follow.objects.get_or_create(follower=follower, following=user_to_follow)

        if created:
            create_notification(sender=follower,receiver=user_to_follow,notification_type='follow')
            return Response({
                "message": f"{follower.username} is now following {user_to_follow.username}"
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                "message": f"{follower.username} is already following {user_to_follow.username}"
            }, status=status.HTTP_200_OK)

class UnfollowUserAPIView(APIView):
    def post(self, request, *args, **kwargs):
        # Get the user to unfollow
        user_to_unfollow_id = kwargs.get('user_id')
        user_to_unfollow = get_object_or_404(User, id=user_to_unfollow_id)
        
        # Get the current user from the request data
        follower = get_object_or_404(User, id=request.data.get('follower_id'))

        # Delete the follow relationship
        try:
            follow = Follow.objects.get(follower=follower, following=user_to_unfollow)
            follow.delete()
            return Response({
                "message": f"{follower.username} has unfollowed {user_to_unfollow.username}"
            }, status=status.HTTP_200_OK)
        except Follow.DoesNotExist:
            return Response({
                "message": f"{follower.username} is not following {user_to_unfollow.username}"
            }, status=status.HTTP_400_BAD_REQUEST)


class ListFollowingAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user_id = kwargs.get('user_id', None)
        user = get_object_or_404(User, id=user_id) if user_id else request.user

        # Retrieve followers
        followers = user.followers.all()

        # Serialize the list of followers
        serializer = UserSerializer([f.follower for f in followers], many=True)
        is_following = Follow.objects.filter(follower=request.user, following=user).exists()

        return Response({
            'followers': serializer.data,
            'is_following': is_following
        }, status=status.HTTP_200_OK)

class ListFollowersAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user_id = kwargs.get('user_id', None)
        user = get_object_or_404(User, id=user_id) if user_id else request.user

        # Retrieve followers
        followers = user.following.all()

        # Serialize the list of followers
        serializer = UserSerializer([f.follower for f in followers], many=True)
        is_following = Follow.objects.filter(follower=request.user, following=user).exists()

        return Response({
            'followers': serializer.data,
            'is_following': is_following
        }, status=status.HTTP_200_OK)


class ListUserConnectionsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user_id = request.query_params.get('user_id', None)
        connection_type = request.query_params.get('type', 'followers')  # 'followers' or 'following'
        search_query = request.query_params.get('search_query', None)

        # Get the user whose connections are being queried
        user = get_object_or_404(User, id=user_id) if user_id else request.user

        # Initialize connections as empty
        connections = []

        # Retrieve the list based on the connection type
        if connection_type == 'followers':
            # Get all users who are following this user
            followers_query = Follow.objects.filter(following=user).order_by('-created_at')
            print(f"Followers for {user.username}:")
            for follow in followers_query:
                print(f"{follow.follower.username} follows {user.username}")
                connections.append(follow.follower)  # Append follower to list of connections
        elif connection_type == 'following':
            # Get all users this user is following
            following_query = Follow.objects.filter(follower=user).order_by('-created_at')
            print(f"{user.username} is following:")
            for follow in following_query:
                print(f"{user.username} follows {follow.following.username}")
                connections.append(follow.following)  # Append following to list of connections
        else:
            return Response({'error': 'Invalid connection type. Use "followers" or "following".'}, status=400)

        # Apply search filter if provided
        if search_query:
            connections = [conn for conn in connections if search_query.lower() in conn.username.lower() or search_query.lower() in conn.email.lower()]

        # Serialize the list of connections
        serializer = UserSerializer(connections, many=True,context={'request': request})

        return Response(serializer.data, status=status.HTTP_200_OK)

class RemoveFollowerAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # Remove a follower by user ID
        follower_to_remove_id = kwargs.get('user_id')
        follower_to_remove = get_object_or_404(User, id=follower_to_remove_id)

        # Get the current user (the user whose followers are being managed)
        current_user = request.user

        try:
            # Delete the follow relationship
            follow = Follow.objects.get(follower=follower_to_remove, following=current_user)
            follow.delete()
            return Response({
                "message": f"{follower_to_remove.username} has been removed from your followers."
            }, status=status.HTTP_200_OK)
        except Follow.DoesNotExist:
            return Response({
                "message": f"{follower_to_remove.username} is not following you."
            }, status=status.HTTP_400_BAD_REQUEST)



class SuggestionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # Get the current user
        current_user = request.user

        # Get the list of users the current user is following
        following_users = Follow.objects.filter(follower=current_user).values_list('following', flat=True)

        # Get the users followed by the users that the current user follows (second-degree connections)
        suggestions = Follow.objects.filter(follower__in=following_users).exclude(following=current_user)

        # Exclude users that the current user is already following
        suggestions = suggestions.exclude(following__in=following_users)

        # Get the list of suggested users (only unique users)
        suggested_users = User.objects.filter(id__in=suggestions.values_list('following', flat=True)).distinct()

        # If no suggestions are found, fetch users that are not followed by the current user
        if not suggested_users:
            # Get all users not followed by the current user, excluding the current user
            suggested_users = User.objects.exclude(id__in=following_users).exclude(id=current_user.id)

            # Order by the number of followers in descending order (most followed first)
            suggested_users = suggested_users.annotate(follower_count=Count('followers')).order_by('-follower_count')[:100]

        # Prepare the response data (username, profile_pic, bio)
        data = [
            {
                'username': user.username,
                'id': user.id,
                'profile_pic': user.profile_pic.url if user.profile_pic else None,
                'bio': user.bio,
            }
            for user in suggested_users
        ]

        return Response(data, status=200)
    
class FeedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        following_ids = [follow.following.id for follow in Follow.objects.filter(follower=user)]
        following_ids.append(user.id)  # Include the user's own posts

        # Get posts from users the current user is following
        posts = Post.objects.filter(user_id__in=following_ids).order_by('-created_at')

        serializer = PostSerializer(posts, many=True, context={'request': request})
        return Response(serializer.data)
    def post(self, request):
        # Create a new post
        post = Post.objects.create(user=request.user, content=request.data['content'])

        # Send a message to the WebSocket channel
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'feed',
            {
                'type': 'send_feed_update',
                'post_id': post.id,
            }
        )

        return Response({'message': 'Post created successfully'}, status=201)

def notify_user_followed(user):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'notifications',  # Use a fixed group name instead of user_id
        {
            'type': 'send_notification',
            'notification': f"You have a new follower: {user.username}",
        }
    )

def notify_user_unfollowed(user):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user.id}",
        {
            'type': 'send_notification',
            'notification': f"You have been unfollowed by: {user.username}",
        }
    )