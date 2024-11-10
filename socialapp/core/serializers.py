from rest_framework import serializers
from .models import User
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model=User
        fields= ['id', 'username', 'first_name', 'email', 'bio', 'dob', 'mobile', 'profile_pic', 'is_active', 'created_at', 'updated_at','cover_pic','is_suspended','is_googleauth','is_online']

    

class RegisterSerializer(serializers.ModelSerializer):
    password=serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'email', 'password', 'bio', 'dob', 'mobile', 'profile_pic']
    def create(self,validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            bio=validated_data.get('bio', ''),
            dob=validated_data.get('dob', None),
            mobile=validated_data.get('mobile', None),
            profile_pic=validated_data.get('profile_pic', None)
        )
        return user
    
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        print(f"Email: {email}, Password: {password}")

        try:
            user = User.objects.get(email=email)
            print(f"User found: {user.username}")
        except User.DoesNotExist:
            print(f"User not found with email: {email}")
            raise serializers.ValidationError('Invalid email or password')

        if not user.check_password(password):
            print(f"Password is incorrect for user: {user.username}")
            raise serializers.ValidationError('Invalid email or password')

        user = authenticate(email=email, password=password)

        if not user:
            print(f"Authentication failed for user: {user.username}")
            raise serializers.ValidationError('Invalid email or password')

        data = super().validate(attrs)
        data['user'] = UserSerializer(user).data
        return data
    
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        user = authenticate(email=email, password=password)

        if not user:
            raise serializers.ValidationError('Invalid email or password')

        return {'user': user}

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    def validate_email(self, value):
        # Check if a user with the provided email exists
        user = User.objects.filter(email=value).first()
        if user:
            # Check if the user is a Google-authenticated user
            if user.is_googleauth:
                raise serializers.ValidationError(
                    "Password reset is not allowed for Google-authenticated users."
                )
        else:
            raise serializers.ValidationError("User with this email does not exist.")
        return value

class PasswordResetConfirmSerializer(serializers.Serializer):
    uidb64 = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)



