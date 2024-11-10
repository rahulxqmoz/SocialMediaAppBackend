from django.shortcuts import render

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count
from core.models import User
from posts.models import Post,Like,Comment
from interactions.models import Follow
from .serializers import UserSerializer, PostSerializer, LikeSerializer, CommentSerializer, FollowSerializer

class ReportViewSet(viewsets.ViewSet):
    """
    A viewset for handling admin reports like weekly user registration,
    total likes, comments, and follows, etc.
    """

    @action(detail=False, methods=['get'])
    def weekly_user_registration(self, request):
        """
        Returns the count of new users registered per day for the last 4 weeks.
        """
        today = timezone.now().date()
        last_4_weeks = today - timedelta(days=56)  # Extends range to 4 weeks

        # Fetch user registrations from the past 4 weeks
        users = User.objects.filter(created_at__date__gte=last_4_weeks)
        
        # Group by day and count the registrations for each day
        daily_counts = (
            users.extra(select={'day': "DATE(created_at)"})
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')  # Order by day to keep it chronological
        )
        
        return Response(daily_counts)

    @action(detail=False, methods=['get'])
    def engagement_stats(self, request):
        """
        Returns total counts of likes, comments, follows, etc.
        """
        total_likes = Like.objects.count()
        total_comments = Comment.objects.count()
        total_follows = Follow.objects.count()

        return Response({
            "total_likes": total_likes,
            "total_comments": total_comments,
            "total_follows": total_follows,
        })

    @action(detail=False, methods=['get'])
    def weekly_post_activity(self, request):
        """
        Returns weekly activity on posts (likes and comments per day).
        """
        today = timezone.now().date()
        last_week = today - timedelta(days=7)

        likes_per_day = Like.objects.filter(created_at__date__gte=last_week).extra(select={'day': "DATE(created_at)"}).values('day').annotate(count=Count('id'))
        comments_per_day = Comment.objects.filter(created_at__date__gte=last_week).extra(select={'day': "DATE(created_at)"}).values('day').annotate(count=Count('id'))

        return Response({
            "likes_per_day": likes_per_day,
            "comments_per_day": comments_per_day,
        })

