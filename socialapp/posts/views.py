from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated,IsAuthenticatedOrReadOnly

from notifications.notifications import create_notification

from .permissions import IsOwnerOrAdmin
from .models import Bookmark, Post, Report,Comment,Like
from .serializers import BookmarkSerializer, PostSerializer, ReportSerializer,CommentSerializer,LikeSerializer
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from .utils import send_suspension_email
# Create your views here.

class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.filter(is_approved=True).order_by('-created_at')  # Filter to show only approved posts
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticatedOrReadOnly,IsOwnerOrAdmin]

    def get_queryset(self):
        """
        Override to allow viewing posts from any user, not just the authenticated user.
        """
        user_id = self.request.query_params.get('user_id', None)
        
        # If user_id is passed, filter posts for that user, otherwise show all posts.
        if user_id:
            return Post.objects.filter(user_id=user_id, is_approved=True).order_by('-created_at')
        
        # Return all approved posts, regardless of the user
        return Post.objects.filter(is_approved=True).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def update(self, request, *args, **kwargs):
        """
        Override the update method to add custom logic if needed.
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response(serializer.data)
    def destroy(self, request, *args, **kwargs):
        """
        Override the destroy method to add custom logic for deleting a post.
        """
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({"detail": "Post deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def check_liked(self, request, pk=None):
        """
        Custom action to check if the user has already liked the post.
        """
        post = self.get_object()
        user = request.user
        liked = Like.objects.filter(user=user, post=post).exists()
        return Response({'liked': liked}, status=status.HTTP_200_OK)
    @action(detail=True, methods=['get'], url_path='comments', permission_classes=[IsAuthenticated])
    def get_comments_for_post(self, request, pk=None):
        """
        Get all comments for a specific post.
        """
        post = self.get_object()  # Retrieves the post instance using the primary key (pk)
        top_level_comments = post.comments.filter(parent=None)
        serializer = CommentSerializer(top_level_comments, many=True)
        return Response(serializer.data)
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def check_bookmarked(self, request, pk=None):
        """
        Custom action to check if the user has bookmarked the post.
        """
        post = self.get_object()
        user = request.user
        bookmarked = Bookmark.objects.filter(user=user, post=post).exists()
        return Response({'bookmarked': bookmarked}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def reported_posts(self, request):
        """
        Returns a list of all reported posts with their report details (reason, additional_info, and reported_by).
        """
        reports = Report.objects.select_related('post', 'reported_by').all().order_by('-created_at')
        reports_data = []
        for report in reports:
            post = report.post
           
            reports_data.append({
                'post_id': post.id,
                'user': post.user.username,
                'profile_pic':post.user.profile_pic.url if post.user.profile_pic else None,
                'content': post.content,  # Assuming you have a content field in your Post model
                'image': post.image.url if post.image else None,  # If using ImageField
                'video': post.video.url if post.video else None,  # If using FileField for video
                'is_reported': post.is_reported,
                'is_approved': post.is_approved,
                'report_details': {
                    'reason': report.reason,
                    'additional_info': report.additional_info,
                    'reported_by': report.reported_by.username
                },
                'created_at': report.created_at,
                
            })
        return Response(reports_data, status=status.HTTP_200_OK)

    # Custom action to suspend a post (mark as reported and disapprove)
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def suspend_post(self, request, pk=None):
        """
        Admin action to suspend a post by setting is_reported to True and is_approved to False.
        """
        post = self.get_object()
        post.is_reported = True
        post.is_approved = False
        post.report_reason = request.data.get('report_reason', 'No reason provided')
        post.save()
        user = post.user  # Assuming the Post model has a ForeignKey to the User model

        # Send suspension email to the user
        send_suspension_email(user, post)

        return Response({
            "detail": "Post has been suspended.",
            "post_id": post.id,
            "is_reported": post.is_reported,
            "is_approved": post.is_approved
        }, status=status.HTTP_200_OK)

    # Custom action to remove suspension (mark as approved and unreport)
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def approve_post(self, request, pk=None):
        """
        Admin action to remove suspension of a post by setting is_reported to False and is_approved to True.
        """
        try:
            post = Post.objects.get(pk=pk)  # Fetch the post even if it's suspended
        except Post.DoesNotExist:
            return Response({"detail": "No Post matches the given query."}, status=status.HTTP_404_NOT_FOUND)
        post.is_reported = False
        post.is_approved = True
        post.report_reason = None  # Clear the report reason if necessary
        post.save()

        return Response({
            "detail": "Post suspension has been removed.",
            "post_id": post.id,
            "is_reported": post.is_reported,
            "is_approved": post.is_approved
        }, status=status.HTTP_200_OK)

class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        post_id = self.request.data.get('post')
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return Response({'error': 'Post does not exist'}, status=status.HTTP_404_NOT_FOUND) 
        serializer.validated_data['reported_by'] = self.request.user
        serializer.validated_data['post'] = post
        if serializer.is_valid():   
            serializer.save(reported_by=self.request.user, post=post, reason=self.request.data['reason'], additional_info=self.request.data['additional_info'])
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all().order_by('-created_at')
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        post_id = self.request.query_params.get('post_id', None)
        user = self.request.user
        
        if post_id:
            # Fetching comments for a specific post, visible to all users
            return Comment.objects.filter(post_id=post_id).order_by('-created_at')
        
        # Default queryset behavior (for user's own posts/comments)
        return Comment.objects.filter(user=self.request.user).order_by('-created_at')
    def perform_create(self, serializer):
        # Save the comment instance
        comment = serializer.save(user=self.request.user)
        
        # Create notification for the post owner (excluding if the user comments on their own post)
        if comment.post.user != self.request.user:
            create_notification(
                sender=self.request.user,
                receiver=comment.post.user,
                notification_type='comment',
                post=comment.post,
                comment=comment
            )

class LikeViewSet(viewsets.ModelViewSet):
    queryset = Like.objects.all().order_by('-created_at')
    serializer_class = LikeSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        user = request.user
        post_id = request.data.get('post')  # Extract post from the request data
        
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)

        # Check if the user already liked the post
        like = Like.objects.filter(user=user, post=post).first()

        if like:
            # If already liked, this will "unlike" the post by deleting the like object
            like.delete()
            return Response({'status': 'Post unliked'}, status=status.HTTP_204_NO_CONTENT)
        else:
            # If not liked yet, this will create a new like
            create_notification(sender=user,receiver=post.user,notification_type='like',post=post)
            new_like = Like.objects.create(user=user, post=post)
            return Response({'status': 'Post liked'}, status=status.HTTP_201_CREATED)

class BookmarkViewSet(viewsets.ModelViewSet):
    queryset = Bookmark.objects.all()
    serializer_class = BookmarkSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        user = request.user
        post_id = request.data.get('post')

        # Ensure the post exists
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)

        # Check if the user already bookmarked the post
        bookmark, created = Bookmark.objects.get_or_create(user=user, post=post)

        if created:
            return Response({'status': 'Post bookmarked'}, status=status.HTTP_201_CREATED)
        else:
            return Response({'status': 'Already bookmarked'}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        user = request.user
        post_id = self.kwargs.get('pk')  # Assuming the post ID is passed as the URL parameter

        # Find the bookmark
        try:
            bookmark = Bookmark.objects.get(user=user, post_id=post_id)
            bookmark.delete()
            return Response({'status': 'Bookmark removed'}, status=status.HTTP_204_NO_CONTENT)
        except Bookmark.DoesNotExist:
            return Response({'error': 'Bookmark not found'}, status=status.HTTP_404_NOT_FOUND)

    def list(self, request, *args, **kwargs):
        # List all bookmarks for the authenticated user
        bookmarks = self.queryset.filter(user=request.user)
        serializer = self.get_serializer(bookmarks, many=True)
        return Response(serializer.data)