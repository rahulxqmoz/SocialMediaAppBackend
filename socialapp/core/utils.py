from django.conf import settings
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives

def send_verification_email(user, request, uidb64, token):
    verification_url = f"{request.scheme}://{request.get_host()}/api/users/verify-email/{uidb64}/{token}/"

    subject = 'Verify Your Email Address'
    html_message = render_to_string('verification_email.html', {
        'username': user.username,
        'verification_url': verification_url,  # Ensure this is passed to the template
    })

    plain_message = f"Hi {user.username},\n\nThank you for registering. Please click the link below to verify your email address:\n\n{verification_url}\n\nIf you did not register for an account, please ignore this email."

    send_mail(
        subject,
        plain_message,
        'rahulraju5555u@gmail.com',  # Your "from" email
        [user.email],
        fail_silently=False,
        html_message=html_message
    )


def send_password_reset_email(user,uidb64,token):

    frontend_base_url = settings.FRONTEND_DOMAIN  
    password_reset_url = f"{frontend_base_url}/password-reset/{uidb64}/{token}"

    # Render email template
    subject = "Password Reset Request"
    html_message = render_to_string('password_reset_email.html', {
        'user': user,
        'password_reset_url': password_reset_url,
    })

    email = EmailMultiAlternatives(
        subject,
        '',  # 
        settings.DEFAULT_FROM_EMAIL,
        [user.email]
    )

    # Attach HTML content
    email.attach_alternative(html_message, "text/html")

    # Send the email
    email.send()