from rest_framework import serializers

from  interactions.models import Follow
from  core.serializers import UserSerializer
from .models import Bookmark, Post, Report,Comment,Like

class PostSerializer(serializers.ModelSerializer):
    total_likes = serializers.SerializerMethodField() 
    total_comments= serializers.SerializerMethodField()
    liked = serializers.SerializerMethodField()
    bookmarked = serializers.SerializerMethodField()
    is_following=serializers.SerializerMethodField()
    report_details = serializers.SerializerMethodField()
    class Meta:
        model = Post
        fields = ['id','user', 'content', 'image', 'video', 'is_reported', 'is_approved', 'report_reason', 'reported_by','created_at','total_likes','total_comments','liked', 'bookmarked','is_following','report_details']

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
    
    def get_report_details(self, obj):
        reports = obj.reports.all()
        return [{
            'reason': report.reason,
            'additional_info': report.additional_info,
            'reported_by': report.reported_by.username
        } for report in reports]

    def validate(self, data):
        # Check for content length
        if 'content' in data and len(data['content']) < 1:
            raise serializers.ValidationError("Post content must be at least 1 characters long.")
        
        # Check for video file size
        video = data.get('video')  # Use get to avoid KeyError if 'video' is not in data
        if video and video.size > 100 * 1024 * 1024:
            raise serializers.ValidationError("Video file size must be less than 100MB.")
        
        return data
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request', None)
        if not request or not request.user.is_staff:
            representation.pop('is_reported', None)
            representation.pop('is_approved', None)
            representation.pop('report_reason', None)
            representation.pop('reported_by', None)
        return representation

class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ['post', 'reported_by', 'reason', 'additional_info', 'created_at']
    
    def validate(self, data):
        # Ensure the same user cannot report the same post more than once
        if Report.objects.filter(post=data['post'], reported_by=data['reported_by']).exists():
            raise serializers.ValidationError({'error': 'You have already reported this post.'})
        return data

    def create(self, validated_data):
        return Report.objects.create(**validated_data)

class CommentSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ('id', 'user','username', 'post', 'parent', 'content', 'created_at', 'replies')

    def validate_content(self, value):
        if not value:
            raise serializers.ValidationError("Comment content cannot be empty.")
        return value

    def validate_parent(self, value):
        if value and not Comment.objects.filter(id=value.id).exists():
            raise serializers.ValidationError("Parent comment does not exist.")
        return value

    def get_replies(self, obj):
        replies = obj.replies.all()  
        return CommentSerializer(replies, many=True).data
    
    def get_username(self, obj):
        return obj.user.username 

class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = ('user', 'post', 'created_at')

class BookmarkPostSerializer(serializers.ModelSerializer):
    total_likes = serializers.SerializerMethodField() 
    total_comments= serializers.SerializerMethodField()
    user = UserSerializer(read_only=True)
    class Meta:
        model = Post
        fields = ['id','user', 'content', 'image', 'video', 'is_reported', 'is_approved', 'report_reason', 'reported_by','created_at','total_likes','total_comments']
    def get_total_likes(self, obj):
        return obj.total_likes()
    def get_total_comments(self, obj):
        return obj.total_comments()
    
class BookmarkSerializer(serializers.ModelSerializer):
    post = BookmarkPostSerializer(read_only=True) 
    class Meta:
        model = Bookmark
        fields = ['user', 'post', 'created_at']