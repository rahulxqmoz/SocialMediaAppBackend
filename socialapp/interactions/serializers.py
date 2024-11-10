from rest_framework import serializers
from .models import Follow
from posts.models import Bookmark, Like, Post
from posts.serializers import CommentSerializer, LikeSerializer
from core.models import User


class SearchQuerySerializer(serializers.Serializer):
    search_query = serializers.CharField(required=True)

    def validate_search_query(self, value):
        if not value:
            raise serializers.ValidationError("Search query cannot be empty.")
        return value

class UserSerializer(serializers.ModelSerializer):
    is_following = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'email', 'bio', 'dob', 'mobile', 'profile_pic', 'cover_pic','is_following','is_online']
    def get_is_following(self, obj):
        request = self.context.get('request')
        if request:
            return Follow.objects.filter(follower=request.user, following=obj).exists()
        return False


class PostSerializer(serializers.ModelSerializer):
    total_likes = serializers.SerializerMethodField() 
    total_comments= serializers.SerializerMethodField()
    user = UserSerializer(read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    likes = LikeSerializer(many=True, read_only=True)
    liked = serializers.SerializerMethodField()
    bookmarked = serializers.SerializerMethodField()
    is_following=serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ['id','user', 'content', 'image', 'video', 'is_reported', 'is_approved', 'report_reason', 'reported_by','created_at','total_likes','total_comments', 'comments', 'likes', 'liked', 'bookmarked','is_following']

    def get_total_likes(self, obj):
        return obj.total_likes()
    def get_total_comments(self, obj):
        return obj.total_comments()

    def get_liked(self, obj):
        user = self.context['request'].user
        return Like.objects.filter(post=obj, user=user).exists()

    def get_bookmarked(self, obj):
        user = self.context['request'].user
        return Bookmark.objects.filter(post=obj, user=user).exists()
    
    def get_is_following(self, obj):
        user = self.context['request'].user
        return Follow.objects.filter(follower=user, following=obj.user).exists()

    def validate(self, data):
        # Check for content length
        if 'content' in data and len(data['content']) < 1:
            raise serializers.ValidationError("Post content must be at least 1 characters long.")
        
        # Check for video file size
        video = data.get('video')  # Use get to avoid KeyError if 'video' is not in data
        if video and video.size > 100 * 1024 * 1024:
            raise serializers.ValidationError("Video file size must be less than 100MB.")
        
        return data