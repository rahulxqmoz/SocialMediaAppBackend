from datetime import timezone
from django.shortcuts import render
from rest_framework.decorators import action
# Create your views here.
from rest_framework import status
from rest_framework import viewsets
from rest_framework.response import Response
from .models import ChatRoom, Message,CallRequest
from .serializers import ChatRoomSerializer, MessageSerializer
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view
from django.db.models import Q
from django.shortcuts import get_object_or_404
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
User = get_user_model() 
class ChatRoomViewSet(viewsets.ViewSet):
    def list(self, request):
        user = request.user
        rooms = ChatRoom.objects.filter(participants=user)
        serializer = ChatRoomSerializer(rooms, many=True, context={'request': request})
        return Response(serializer.data)

    def create(self, request):
        user1 = request.user  # The currently authenticated user
        participants = request.data.get('participants', [])

        # Ensure the current user is included in participants
        if user1.id not in participants:
            participants.append(user1.id)

        # Ensure exactly two participants
        if len(participants) != 2:
            return Response({"error": "Invalid participants."}, status=status.HTTP_400_BAD_REQUEST)

        # Get the second user

        user2_id = [p for p in participants if p != user1.id][0]
        try:
            user2 = User.objects.get(id=user2_id)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        # Ensure room uniqueness for two users
        room_name = f"room_{min(user1.id, user2.id)}_{max(user1.id, user2.id)}"
        room, created = ChatRoom.objects.get_or_create(room_name=room_name)
        room.participants.add(user1, user2)

        serializer = ChatRoomSerializer(room, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'], url_path='create-group')
    def create_group(self, request):
        user = request.user
        group_name = request.data.get('group_name')
        participants = request.data.get('participants', [])

        # Ensure the current user is included in participants
        if user.id not in participants:
            participants.append(user.id)

        # Create a group chat
        room, created = ChatRoom.objects.get_or_create(group_name=group_name, is_group=True)
        room.participants.set(participants)

        serializer = ChatRoomSerializer(room,context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='user-groups')
    def list_groups(self, request):
        user = request.user
        groups = ChatRoom.objects.filter(participants=user, is_group=True)
        serializer = ChatRoomSerializer(groups, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='leave-group')
    def leave_group(self, request, pk=None):
        user = request.user
        try:
            group = ChatRoom.objects.get(pk=pk, is_group=True)
            group.participants.remove(user)
            if group.participants.count() == 0:
                group.delete()  # Delete group if no participants left
            return Response({"success": "Left group successfully."}, status=status.HTTP_200_OK)
        except ChatRoom.DoesNotExist:
            return Response({"error": "Group not found."}, status=status.HTTP_404_NOT_FOUND)
        
    def retrieve(self, request, pk=None):
        try:
            room = ChatRoom.objects.get(pk=pk)
        except ChatRoom.DoesNotExist:
            return Response({"error": "Room not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ChatRoomSerializer(room, context={'request': request})
        return Response(serializer.data)

class MessageViewSet(viewsets.ViewSet):
    def list(self, request, room_name):
        try:
            room = ChatRoom.objects.get(room_name=room_name)
            messages = Message.objects.filter(room=room).order_by('timestamp')
            serializer = MessageSerializer(messages, many=True)
            return Response(serializer.data)
        except ChatRoom.DoesNotExist:
            return Response({"error": "Chat room not found."}, status=status.HTTP_404_NOT_FOUND)
        
    @action(detail=False, methods=['get'], url_path='older/(?P<oldest_message_id>[^/.]+)')
    def older_messages(self, request, room_name, oldest_message_id):
        try:
            room = ChatRoom.objects.get(room_name=room_name)
            messages = Message.objects.filter(room=room, id__lt=oldest_message_id).order_by('-timestamp')[:10]  # Fetch 10 older messages
            serializer = MessageSerializer(messages, many=True)
            return Response(serializer.data)
        except ChatRoom.DoesNotExist:
            return Response({"error": "Chat room not found."}, status=status.HTTP_404_NOT_FOUND)

    def create(self, request, room_name):
        room = ChatRoom.objects.get(room_name=room_name)

        message_type = request.data.get('message_type', 'text')
        message = request.data.get('message', '')
        file = request.FILES.get('file', None)  # Handle file upload

        if file:
            new_message = Message.objects.create(
                room=room,
                sender=request.user,
                message=message if message_type == 'text' else None,
                file=file,
                message_type=message_type
            )
        else:
            new_message = Message.objects.create(
                room=room,
                sender=request.user,
                message=message,
                message_type=message_type
            )
        serializer = MessageSerializer(new_message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'], url_path='list-with-id/(?P<room_id>\d+)')
    def list_with_id(self, request, room_id):
        """List messages using the room ID."""
        try:
            room = ChatRoom.objects.get(id=room_id)
            messages = Message.objects.filter(room=room).order_by('timestamp')
            serializer = MessageSerializer(messages, many=True)
            return Response(serializer.data)
        except ChatRoom.DoesNotExist:
            return Response({"error": "Chat room not found."}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'], url_path='create-with-id')
    def create_with_id(self, request):
        # Fetch the room by ID instead of room_name
        room_id = request.data.get('room_id')
        room = get_object_or_404(ChatRoom, id=room_id)
        return self._create_message(request, room)

    def _create_message(self, request, room):
        message_type = request.data.get('message_type', 'text')
        message = request.data.get('message', '')
        file = request.FILES.get('file', None)

        if file:
            new_message = Message.objects.create(
                room=room,
                sender=request.user,
                message=message if message_type == 'text' else None,
                file=file,
                message_type=message_type
            )
        else:
            new_message = Message.objects.create(
                room=room,
                sender=request.user,
                message=message,
                message_type=message_type
            )
        
        serializer = MessageSerializer(new_message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    

@api_view(['GET'])
def get_unread_counts(request):
    user_id = request.user.id
    unread_counts = {}
     # Get all users except the current user
    users = User.objects.exclude(id=user_id)

    for user in users:
        room_name = f"room_{min(user_id, user.id)}_{max(user_id, user.id)}"

        # Try to fetch the chat room
        try:
            room = ChatRoom.objects.get(room_name=room_name)
            
            # Count messages in the room sent by the other user
            unread_messages = Message.objects.filter(
                room=room,
                sender=user,  # Messages sent by the other user
            ).filter(~Q(read_by__id=user_id)).count()  # Messages not read by the current user
            
            unread_counts[user.id] = unread_messages
        except ChatRoom.DoesNotExist:
            # If the room does not exist, set count to 0
            unread_counts[user.id] = 0

    return Response(unread_counts)

@api_view(['POST'])
def initiate_call(request):
    caller = request.user
    recipient_id = request.data.get('recipient_id')
    recipient = get_object_or_404(User, id=recipient_id)
    offer=request.data.get('offer')
    print(f"Offer: {offer}")

    call_request = CallRequest.objects.create(caller=caller, recipient=recipient)

    # Notify the recipient via WebSocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"usercall_{recipient.id}",  # The group name based on the recipient's user ID
        {
            'type': 'notify_call',  # Custom event type handled in CallConsumer
            'caller': caller.username,
            'call_id': call_request.id,
            'status': call_request.status,
            'caller_id': caller.id,
            'offer':offer,
        }
    )

    return Response({"message": "Call initiated","call_request": call_request.id}, status=status.HTTP_201_CREATED)

@api_view(['POST'])
def accept_call(request, call_id):
    # Get the call request by ID and ensure the recipient is the one accepting
    call_request = get_object_or_404(CallRequest, id=call_id, recipient=request.user)
    
    # Update status to 'active'
    call_request.status = 'active'
    call_request.save()

    # Notify the caller
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"usercall_{call_request.caller.id}",
        {
            'type': 'notify_call',
            'caller': call_request.caller.username,
            'call_id': call_request.id,
            'status': call_request.status,
            'caller_id': call_request.caller.id,
            'offer':None,
        }
    )

    return Response({"message": "Call accepted"}, status=status.HTTP_200_OK)

@api_view(['POST'])
def decline_call(request, call_id):
    call_request = get_object_or_404(CallRequest, id=call_id, recipient=request.user)
    
    # Update status to 'declined'
    call_request.status = 'declined'
    call_request.save()

    # Notify the caller
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"usercall_{call_request.caller.id}",
        {
            'type': 'notify_call',
            'caller': call_request.caller.username,
            'call_id': call_request.id,
            'status': call_request.status,
            'caller_id': call_request.recipient.id,
            'offer':None,
        }
    )

    return Response({"message": "Call declined"}, status=status.HTTP_200_OK)
@api_view(['POST'])
def end_call(request, call_id):
    # Get the call request by ID and ensure either the caller or recipient is ending the call
    call_request = get_object_or_404(CallRequest, id=call_id)
    
    if request.user not in [call_request.caller, call_request.recipient]:
        return Response({"error": "You are not a part of this call"}, status=status.HTTP_403_FORBIDDEN)

    # Update status to 'ended'
    call_request.status = 'ended'
    call_request.ended_at = timezone.now()
    call_request.save()

    # Notify both caller and recipient
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"usercall_{call_request.caller.id}",
        {
            'type': 'notify_call',
            'caller': call_request.caller.username,
            'call_id': call_request.id,
            'status': call_request.status,
            'caller_id': call_request.caller.id,
            'offer':None,
        }
    )
    async_to_sync(channel_layer.group_send)(
        f"user_{call_request.recipient.id}",
        {
            'type': 'notify_call',
            'caller': call_request.caller.username,
            'call_id': call_request.id,
            'status': call_request.status,
            'caller_id': call_request.recipient.id,
            'offer':None,
        }
    )

    return Response({"message": "Call ended"}, status=status.HTTP_200_OK)
