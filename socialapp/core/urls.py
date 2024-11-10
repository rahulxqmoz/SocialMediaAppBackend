from django.urls import path
from .views import AdminUserListView, BlockUserView, GoogleAuthView, GoogleLogin, PasswordResetConfirmView, PasswordResetRequestView, RegisterView,LoginView,CustomTokenObtainPairView, UpdatePasswordView, UpdateProfileView, UserProfileView,verify_email,check_verification_token,activate_user,VerifyEmailView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns=[
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('verify-email/<str:uidb64>/<str:token>/', verify_email, name='verify-email'),
    path('check-token/<uidb64>/<token>/', check_verification_token, name='check_token'),
    path('activate/<uidb64>/<token>/', activate_user, name='activate_user'),
    path('password-reset-request/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('validate-mail/', VerifyEmailView.as_view(), name='validate-mail'),
    path('accounts/google/login/', GoogleLogin.as_view(), name='google_login'),
    path('profile/<int:user_id>/', UserProfileView.as_view(), name='user-profile'),
    path('admin/users/', AdminUserListView.as_view(), name='admin_user_list'),
    path('admin/users/<int:pk>/block/', BlockUserView.as_view(), name='block-user'),
    path('profile/update/', UpdateProfileView.as_view(), name='update-profile'),
    path('password/update/', UpdatePasswordView.as_view(), name='update-password'),
    path('google-signup/', GoogleAuthView.as_view(), name='google-signup'),
    
]
