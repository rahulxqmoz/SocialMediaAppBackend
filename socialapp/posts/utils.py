from django.core.mail import send_mail
from django.template.loader import render_to_string

def send_suspension_email(user, post):
    subject = 'Your Post Has Been Suspended'
    html_message = render_to_string('suspension_email.html', {
        'username': user.username,
        'post_title': post.content,  # Assuming the post has a title field
        'post_id': post.id,
        'reason': post.report_reason,
    })

    plain_message = f"Hi {user.username},\n\nYour post titled '{post.content}' has been suspended for the following reason:\n\n{post.report_reason}\n\nIf you have any questions, please contact support."

    send_mail(
        subject,
        plain_message,
        'rahulraju5555u@gmail.com',  
        [user.email], 
        fail_silently=False,
        html_message=html_message
    )
