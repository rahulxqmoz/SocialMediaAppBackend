from channels.generic.websocket import AsyncWebsocketConsumer
import json
from datetime import datetime
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from urllib.parse import parse_qs
import jwt
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.conf import settings
import logging
from .models import ChatRoom,Message
from django.db.models import Q
from jwt import decode as jwt_decode, InvalidTokenError
import re
User = get_user_model()
logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'

        self.user = None

        # Extract token from the query string
        query_params = parse_qs(self.scope['query_string'].decode())
        token_key = query_params.get('token', [None])[0]
        
        if token_key:
            logger.info(f"Token found: {token_key}")
            self.user = await self.get_user_from_token(token_key)
            if self.user:
                logger.info(f"User {self.user.username} connected")
                
                # Mark the user as online
                await self.set_user_online(self.user)

                # Join the room group
                await self.channel_layer.group_add(
                    self.room_group_name,
                    self.channel_name
                )
                await self.accept()
            else:
                logger.error(f"Invalid token or user not found for token: {token_key}")
                await self.close()
        else:
            logger.error("No token found in query string")
            await self.close()

    async def disconnect(self, close_code):
        if self.user:
            # Mark the user as offline when the WebSocket is disconnected
            await self.set_user_offline(self.user)

        # Leave the room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        
        if 'type' in data and data['type'] == 'message_sent':
            # Broadcast the message to the group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': 'Message sent',
                    'sender': data['sender'],
                    'timestamp': data['timestamp'],
                    'message_id': data['message_id'],  
                    
                }
            )

            await self.broadcast_unread_counts_to_all_users()
            
          
        

        elif 'type' in data and data['type'] == 'message_read':
        # Mark the message as read
            message_id = data['message_id']
            user_id = data['user_id']
            await self.mark_message_as_read(message_id, user_id)  # Add user to read_by

            updated_message = await self.get_updated_message(message_id)
            if updated_message:  # Ensure updated_message is not None
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': 'Message read',
                        'updated_message': updated_message,  # This is now a dict
                    }
                )
            else:
                logger.error(f"Failed to get updated message for id {message_id}.")

            await self.broadcast_unread_counts_to_all_users()


   
    async def chat_message(self, event):
        if 'updated_message' in event:
            updated_message = event['updated_message']
            await self.send(text_data=json.dumps({
                'type': 'message_read',  # Specify the type for the frontend to identify
                'message_id': updated_message['id'],
                'read_by': updated_message['read_by'],  # Include the updated read_by list
                'timestamp': updated_message['timestamp'],  # Include timestamp if needed
            }))
        else:    
            room = await self.get_room()
            latest_message = await database_sync_to_async(
            lambda: Message.objects.filter(room=room).select_related('sender').latest()
            )()

            # if 'updated_message' in event:
            #     latest_message = event['updated_message']

            if latest_message:  # Check if there is a message
                # Send the latest message to WebSocket
                read_by_list = await self.get_read_by_list(latest_message)

                await self.send(text_data=json.dumps({
                    'message': latest_message.message,
                    'file': latest_message.file.url if latest_message.file else None,
                    'message_type': latest_message.message_type,
                    'sender': latest_message.sender.id,
                    'timestamp': latest_message.timestamp.isoformat(),
                    'read_by':read_by_list,
                    'message_id':latest_message.id
                    
                }))
            else:
                # Optionally handle the case where there are no messages
                await self.send(text_data=json.dumps({
                    'message': 'No messages in this chat room.',
                    'sender': None,
                    'timestamp': datetime.now().isoformat(),
                }))


    async def get_room(self):
        room_name = self.scope['url_route']['kwargs']['room_name']
        room = await database_sync_to_async(ChatRoom.objects.get)(room_name=room_name)
        return room

    async def save_message(self, room, message, user_id, message_type, file=None):
        user = await database_sync_to_async(User.objects.get)(id=user_id)
        await database_sync_to_async(Message.objects.create)(
            room=room,
            sender=user,
            message=message if message_type == 'text' else None,
            file=file  if message_type in ['image', 'gif', 'video'] else None,
            message_type=message_type
        )
        
        
    

    async def broadcast_unread_counts_to_all_users(self):
        """
        Calculate unread message counts for each user and send it through the NotificationConsumer.
        """
        all_users = await database_sync_to_async(lambda: list(User.objects.all()))()
        unread_counts = {}

        # Calculate unread counts for each user
        for user in all_users:
            unread_count = await self.get_unread_count_for_user(user)
            unread_counts[str(user.id)] = unread_count

        for user in all_users:
            await self.channel_layer.group_send(
                f"unreadnotifications_{user.id}",  # Make sure this matches the group name used in NotificationConsumer
                {
                    "type": "send_unread_counts",  # This type must match the handler name in NotificationConsumer
                    "unread_counts": unread_counts,
                }
            )
   
  


    @database_sync_to_async
    def get_user_from_token(self, token_key):
        try:
            # Decode and validate the JWT token
            UntypedToken(token_key)
            decoded_data = jwt.decode(token_key, settings.SECRET_KEY, algorithms=['HS256'])

            # Extract user ID from the token payload
            user_id = decoded_data.get('user_id')
            return User.objects.get(id=user_id)
        except (InvalidToken, TokenError, User.DoesNotExist) as e:
            logger.error(f"Token error: {e}")
            return None

    @database_sync_to_async
    def set_user_online(self, user):
        user.is_online = True
        user.save()

    @database_sync_to_async
    def set_user_offline(self, user):
        user.is_online = False
        user.save()

    @database_sync_to_async
    def mark_message_as_read(self, message_id, user_id):
        try:
            message = Message.objects.get(id=message_id)
            message.read_by.add(user_id)
            message.save()
        except Message.DoesNotExist:
            logger.error(f"Message with id {message_id} does not exist.")

    @database_sync_to_async
    def get_read_by_list(self,message):
       return list(message.read_by.values_list('id', flat=True))
    @database_sync_to_async
    def get_updated_message(self, message_id):
        message = Message.objects.filter(id=message_id).select_related('sender').first()
        if not message:
            logger.error(f"Message with id {message_id} does not exist.")
            return None

        return {
            'id': message.id,
            'message': message.message,
            'sender': message.sender.id,
            'timestamp': message.timestamp.isoformat(),
            'read_by': list(message.read_by.values_list('id', flat=True)),
            # Include any other fields you want to send
        }
    @database_sync_to_async
    def get_unread_count_for_user(self, user):
        # Calculate unread messages for a given user (implement your logic here)
        user_id = user.id
        unread_counts = {}
        users = User.objects.exclude(id=user_id)

        for other_user in users:
            room_name = f"room_{min(user_id, other_user.id)}_{max(user_id, other_user.id)}"
            try:
                room = ChatRoom.objects.get(room_name=room_name)
                unread_messages = Message.objects.filter(
                    room=room,
                    sender=other_user,
                ).filter(~Q(read_by__id=user_id)).count()
                unread_counts[other_user.id] = unread_messages
            except ChatRoom.DoesNotExist:
                unread_counts[other_user.id] = 0

        return {str(k): v for k, v in unread_counts.items()}

   
class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.group_name = f"unreadnotifications_{self.user_id}"  # Group name format

        # Join the notifications group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        # This consumer only listens for events; it does not receive data from the client.
        pass

    async def send_unread_counts(self, event):
        unread_counts = event.get('unread_counts', {})
        await self.send(text_data=json.dumps({
            'type': 'unread_counts',  # This type can be used by the frontend to identify the message
            'unread_counts': unread_counts
        }))
    
class GroupChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'group_chat_{self.room_name}'
        self.user = None

        # Extract token from the query string
        query_params = parse_qs(self.scope['query_string'].decode())
        token_key = query_params.get('token', [None])[0]

        if token_key:
            self.user = await self.get_user_from_token(token_key)
            if self.user:
                # Mark the user as online and join the room group
                await self.set_user_online(self.user)
                await self.channel_layer.group_add(self.room_group_name, self.channel_name)
                await self.accept()
            else:
                await self.close()
        else:
            await self.close()

    async def disconnect(self, close_code):
        if self.user:
            await self.set_user_offline(self.user)
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get('message', '')  # Set a default empty message if not provided
        message_type = data.get('message_type', 'text')
        timestamp = data.get('timestamp', '')

        if 'type' in data and data['type'] == 'message_sent':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'sender': self.user.username,
                    'message_type': message_type,
                    'timestamp':timestamp,
                }
            )
        elif 'type' in data and data['type'] == 'message_read':
        # Mark the message as read
            message_id = data['message_id']
            user_id = data['user_id']
            await self.mark_message_as_read(message_id, user_id)  # Add user to read_by

            updated_message = await self.get_updated_message(message_id)
            if updated_message:  # Ensure updated_message is not None
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': 'Message read',
                        'updated_message': updated_message,  # This is now a dict
                    }
                )
            else:
                logger.error(f"Failed to get updated message for id {message_id}.")

    async def chat_message(self, event):
        if 'updated_message' in event:
            updated_message = event['updated_message']
            await self.send(text_data=json.dumps({
                'type': 'message_read',  # Specify the type for the frontend to identify
                'message_id': updated_message['id'],
                'read_by': updated_message['read_by'],  # Include the updated read_by list
                'timestamp': updated_message['timestamp'],  # Include timestamp if needed
            }))
        else:  
            room = await self.get_room()
            latest_message = await database_sync_to_async(
                lambda: Message.objects.filter(room=room).select_related('sender').latest()
            )()

            if latest_message:
                read_by_list = await self.get_read_by_list(latest_message)

                await self.send(text_data=json.dumps({
                    'message': latest_message.message,
                    'file': latest_message.file.url if latest_message.file else None,
                    'message_type': latest_message.message_type,
                    'sender': latest_message.sender.id,
                    'timestamp': latest_message.timestamp.isoformat(),
                    'read_by': read_by_list,
                    'message_id': latest_message.id,
                    'sender_username': latest_message.sender.username,
                    'sender_profile_pic': latest_message.sender.profile_pic.url if latest_message.sender.profile_pic else None,
                }))
            else:
                await self.send(text_data=json.dumps({
                    'message': 'No messages in this chat room.',
                    'sender': None,
                    'timestamp': datetime.now().isoformat(),
                }))
    @database_sync_to_async
    def get_user_from_token(self, token_key):
        try:
            UntypedToken(token_key)
            decoded_data = jwt_decode(token_key, settings.SECRET_KEY, algorithms=['HS256'])
            user_id = decoded_data.get('user_id')
            return User.objects.get(id=user_id)
        except (InvalidTokenError, User.DoesNotExist) as e:
            logger.error(f"Token error: {e}")
            return None

    @database_sync_to_async
    def set_user_online(self, user):
        user.is_online = True
        user.save()

    @database_sync_to_async
    def set_user_offline(self, user):
        user.is_online = False
        user.save()

    @database_sync_to_async
    def save_message(self, room_name, message, user_id, message_type, file=None):
        room = ChatRoom.objects.get(room_name=room_name)
        user = User.objects.get(id=user_id)
        return Message.objects.create(
            room=room,
            sender=user,
            message=message if message_type == 'text' else None,
            file=file if message_type in ['image', 'gif', 'video'] else None,
            message_type=message_type
        )
    @database_sync_to_async
    def get_read_by_list(self,message):
       return list(message.read_by.values_list('id', flat=True))
    
    @database_sync_to_async
    def get_room(self):
        try:
            return ChatRoom.objects.get(id=self.room_name)
        except ChatRoom.DoesNotExist:
            return None
        
    @database_sync_to_async
    def mark_message_as_read(self, message_id, user_id):
        try:
            message = Message.objects.get(id=message_id)
            message.read_by.add(user_id)
            message.save()
        except Message.DoesNotExist:
            logger.error(f"Message with id {message_id} does not exist.")

    @database_sync_to_async
    def get_updated_message(self, message_id):
        message = Message.objects.filter(id=message_id).select_related('sender').first()
        if not message:
            logger.error(f"Message with id {message_id} does not exist.")
            return None

        return {
            'id': message.id,
            'message': message.message,
            'sender': message.sender.id,
            'timestamp': message.timestamp.isoformat(),
            'read_by': list(message.read_by.values_list('id', flat=True)),
            # Include any other fields you want to send
        }



class VideoCallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.caller_id = self.scope['url_route']['kwargs']['caller_id']
        sorted_ids = sorted([self.user_id, self.caller_id])
        self.room_group_name = f"video_call_{sorted_ids[0]}_{sorted_ids[1]}"
        print(self.room_group_name)
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')

        if action == 'video_call_offer':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'send_offer',
                    'offer': data['offer'],
                    'recipient_id': data['recipient_id'],
                    'sender_username': data['sender_username']
                }
            )

        elif action == 'video_call_answer':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'send_answer',
                    'answer': data['answer'],
                    'recipient_id': data['recipient_id']
                }
            )

        elif action == 'ice_candidate':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'send_candidate',
                    'candidate': data['candidate'],
                    'recipient_id': data['recipient_id']
                }
            )

        elif action == 'end_call':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'call_ended',
                    'sender_id': data['sender_id'],
                    'recipient_id': data['recipient_id']
                }
            )

    async def send_offer(self, event):
        await self.send(text_data=json.dumps({
            'action': 'video_call_offer',
            'offer': event['offer'],
            'sender_username': event['sender_username']
        }))

    async def send_answer(self, event):
        await self.send(text_data=json.dumps({
            'action': 'video_call_answer',
            'answer': event['answer']
        }))

    async def send_candidate(self, event):
        await self.send(text_data=json.dumps({
            'action': 'ice_candidate',
            'candidate': event['candidate']
        }))

    async def call_ended(self, event):
        await self.send(text_data=json.dumps({
            'action': 'end_call',
            'sender_id': event['sender_id']
        }))
    

def sanitize_room_name(room_name):
    # Replace disallowed characters with an underscore and remove any non-ASCII characters
    sanitized = re.sub(r'[^a-zA-Z0-9_.-]', '_', room_name)
    return sanitized[:100]  # Ensure length is within limits


class CallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.user = None

        # Extract token from the query string
        query_params = parse_qs(self.scope['query_string'].decode())
        token_key = query_params.get('token', [None])[0]

        if token_key:
            logger.info(f"Token found: {token_key}")
            self.user = await self.get_user_from_token(token_key)
            if self.user:
                logger.info(f"User {self.user.username} connected.")
                # Create a group for the authenticated user
                self.group_name = f"usercall_{self.user.id}"
                await self.channel_layer.group_add(self.group_name, self.channel_name)
                await self.accept()
            else:
                logger.error(f"Invalid token or user not found for token: {token_key}")
                await self.close()
        else:
            logger.error("No token found in query string")
            await self.close()

    async def disconnect(self, close_code):
        if self.user.is_authenticated:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            logger.info(f"User {self.user.username} disconnected.")

    async def receive(self, text_data):
        # Process any data received from WebSocket, if needed
        pass

    async def notify_call(self, event):
        await self.send(text_data=json.dumps({
            'type': 'call_notification',
            'caller': event['caller'],
            'call_id': event['call_id'],
            'status': event['status'],
            'caller_id': event['caller_id'],
            'offer':event['offer'],
        }))

    @database_sync_to_async
    def get_user_from_token(self, token_key):
        try:
            # Decode and validate the JWT token
            UntypedToken(token_key)
            decoded_data = jwt.decode(token_key, settings.SECRET_KEY, algorithms=['HS256'])

            # Extract user ID from the token payload
            user_id = decoded_data.get('user_id')
            return User.objects.get(id=user_id)
        except (InvalidToken, TokenError, User.DoesNotExist) as e:
            logger.error(f"Token error: {e}")
            return None