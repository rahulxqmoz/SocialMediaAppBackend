from django.conf import settings
from django.shortcuts import render
import requests
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status,generics,permissions,serializers
from rest_framework.views import APIView
from django.utils.http import urlsafe_base64_encode
from interactions.models import Follow
from .models import User
from .serializers import CustomTokenObtainPairSerializer, PasswordResetConfirmSerializer, PasswordResetRequestSerializer, RegisterSerializer, UserSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import AccessToken,RefreshToken
from .serializers import LoginSerializer
from rest_framework.authtoken.models import Token
from django.utils.encoding import force_str ,force_bytes
from .utils import send_password_reset_email, send_verification_email
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.http import HttpResponse, JsonResponse
from django.core.mail import send_mail
from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from django.utils.timezone import now, timedelta
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from google.oauth2 import id_token
from google.auth.transport.requests import Request
# Create your views here.
class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()  # Save the user
            user.is_active = False  # Set user as inactive until email is verified
            user.save()

            # Generate the token and UID
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            # Send verification email
            send_verification_email(user, request, uidb64, token)

            # Generate refresh and access tokens
            refresh = RefreshToken.for_user(user)

            # Send response
            return Response({
                'access_token': str(refresh.access_token),  # Access token
                'refresh_token': str(refresh),  # Refresh token
                'uidb64': uidb64,  
                'token': token,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'first_name': user.first_name,
                    'profile_pic': user.profile_pic.url if user.profile_pic else None,
                    'is_active':user.is_active

                }
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
def verify_email(request, uidb64, token):
    try:
        # Decode the user ID from the base64 string
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if not user.is_active:  # Check if the user is already active
            user.is_active = True  # Mark the user as active after email verification
            user.save()
            
            context = {
                'frontend_base_url': settings.FRONTEND_DOMAIN,
            }
            return render(request, 'email_verified.html', context)
        else:
            return HttpResponse('User is already verified.')  
    else:
        return HttpResponse('Verification link is invalid or has expired.')
    
def check_verification_token(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        return JsonResponse({'status': 'valid'})
    else:
        return JsonResponse({'status': 'invalid'})

def activate_user(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if not user.is_active:
            user.is_active = True
            user.save()
            return JsonResponse({'status': 'activated'})
        else:
            return JsonResponse({'status': 'already_activated'})
    else:
        return JsonResponse({'status': 'invalid'})
    
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class LoginView(APIView):
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        is_staff=user.is_staff
        token = AccessToken.for_user(user)
        response_data = {
            'token': str(token),
            'is_admin': user.is_staff,
            'id': user.id,  
            'username': user.username,  
            'first_name': user.first_name,  
            'profile_pic': user.profile_pic.url if user.profile_pic else None  ,
            'is_active':user.is_active,
            'is_suspended':user.is_suspended,
            'is_googleauth':user.is_googleauth

        }

        return Response(response_data, status=status.HTTP_200_OK)

class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = User.objects.filter(email=email).first()
            if user:
               
                token = default_token_generator.make_token(user)
                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                send_password_reset_email(user, uidb64, token)  
            return Response({'detail': 'Password reset link has been sent to your email if it exists in our system.'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            uidb64 = serializer.validated_data['uidb64']
            token = serializer.validated_data['token']
            new_password = serializer.validated_data['new_password']
            try:
                uid = urlsafe_base64_decode(uidb64).decode()
                user = User.objects.get(pk=uid)
            except (TypeError, ValueError, OverflowError, User.DoesNotExist):
                user = None

            if user is not None and default_token_generator.check_token(user, token):
                user.set_password(new_password)
                user.save()
                return Response({'detail': 'Password has been reset successfully.'})
            else:
                return Response({'detail': 'Invalid or expired token.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyEmailView(APIView):
    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        if not email:
            return Response({"detail": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        # API endpoint and parameters
        api_url = "http://apilayer.net/api/check"
        api_key = settings.EMAIL_VERIFICATION_API_KEY  # Store API key in Django settings
        params = {
            'access_key': api_key,
            'email': email,
            'smtp': 1,
            'format': 1
        }

        try:
            # Make a request to the email verification service
            response = requests.get(api_url, params=params)
            result = response.json()

            # Check the response and verify if the email is valid
            if result.get("smtp_check") == "true" and result.get("format_valid") == "true":
                return Response({"detail": "Email is valid."}, status=status.HTTP_200_OK)
            else:
                return Response({"detail": "Email is not valid or does not exist."}, status=status.HTTP_400_BAD_REQUEST)
        except requests.RequestException as e:
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter

def validate_token(token):
    try:
        # Validate the token using JWTAuthentication
        validated_token = JWTAuthentication().get_validated_token(token)
        return True
    except (InvalidToken, TokenError) as e:
        print(f"Token validation error: {e}")
        return False

class UserProfileView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    
    def get(self, request, user_id):
        # Example of checking if the token is valid
        token = request.headers.get('Authorization', '').split(' ')[-1]  # Extract token from Authorization header
        if not validate_token(token):
            return Response({"detail": "Invalid or expired token."}, status=status.HTTP_401_UNAUTHORIZED)

        user = get_object_or_404(User, id=user_id)
        is_following = Follow.objects.filter(follower=request.user, following=user).exists()
        followers_count = Follow.objects.filter(following=user).count()  
        following_count = Follow.objects.filter(follower=user).count()
        # Prepare the response data
        response_data = {
            'id': user.id,
            'first_name': user.first_name,
            'username': user.username,
            'email': user.email,
            'bio': user.bio,
            'dob': user.dob,
            'mobile': user.mobile,
            'is_active': user.is_active,
            'created_at': user.created_at,
            'is_active': user.updated_at,
            'is_suspended': user.is_googleauth,
            'is_active': user.updated_at,
            'profile_pic': user.profile_pic.url if user.profile_pic else None,
            'cover_pic': user.cover_pic.url if user.cover_pic else None,
            'followers': followers_count,
            'following': following_count,
            'is_following': is_following,
        }
        return Response(response_data, status=status.HTTP_200_OK)

class AdminUserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]

class BlockUserView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def patch(self, request, pk, *args, **kwargs):
        # Get the user object
        user = get_object_or_404(User, pk=pk)
        
        # Toggle the is_suspended field
        user.is_suspended = not user.is_suspended
        user.save()

        # Serialize the updated user and return a response
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

class UpdateProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        user = request.user
        serializer = UserSerializer(user, data=request.data, partial=True)
        
        if serializer.is_valid():
            # Check if username is being updated and is unique
            if 'username' in serializer.validated_data:
                new_username = serializer.validated_data['username']
                if User.objects.exclude(pk=user.pk).filter(username=new_username).exists():
                    return Response({'detail': 'Username already exists.'}, status=status.HTTP_400_BAD_REQUEST)

            # Save the updated user details
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UpdatePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        user = request.user
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')

        if not current_password or not new_password:
            return Response({'detail': 'Both current and new passwords are required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if the current password is correct
        if not user.check_password(current_password):
            return Response({'detail': 'Current password is incorrect.'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate new password
        try:
            validate_password(new_password, user)
        except ValidationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Set the new password and save the user
        user.set_password(new_password)
        user.save()

        # Update the session hash to keep the user logged in
        update_session_auth_hash(request, user)

        return Response({'detail': 'Password has been updated successfully.'}, status=status.HTTP_200_OK)
    


class GoogleAuthView(APIView):
    def post(self, request):
        token = request.data.get('token')
        try:
            # Verify the token with Google's servers
            id_info = id_token.verify_oauth2_token(token, Request(), settings.GOOGLE_CLIENT_ID)

            # Extract user information
            email = id_info['email']
            first_name = id_info['given_name']
            profile_picture = id_info.get('picture')  # Get the profile picture URL

            # Check if user already exists
            user, created = User.objects.get_or_create(email=email, defaults={
                'username': email.split('@')[0],
                'first_name': first_name,
                'is_active': True,
                'is_googleauth':True,
            })

            # Update profile picture if needed
            # if profile_picture and (user.profile_pic != profile_picture):
            #     user.profile_pic = profile_picture
            #     user.save()

            # Generate uidb64 and token for user
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            token  = AccessToken.for_user(user)

            response_data = {
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'is_suspended': user.is_suspended,
                    'is_admin': user.is_staff,
                    'username': user.username,
                    'profile_pic': user.profile_pic.url if user.profile_pic else None,
                },
                'uidb64': uidb64,
                'token': str(token)
            }

            # Return appropriate response
            return Response({
                'is_new_user': created,
                **response_data
            }, status=status.HTTP_200_OK)

        except ValueError:
            # Invalid token
            return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)
        
        