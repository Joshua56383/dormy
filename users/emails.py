import os
import sys
import logging
from datetime import timedelta
from email.mime.image import MIMEImage
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

# Ensure UTF-8 output on Windows terminal consoles
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

logger = logging.getLogger(__name__)

def _get_dormy_logo_mime():
    """
    Locates static/images/logo.png and returns an inline MIMEImage object
    with Content-ID <dormy_logo> for flawless rendering across all email clients.
    """
    possible_paths = [
        os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png'),
        os.path.join(settings.BASE_DIR, 'staticfiles', 'images', 'logo.png'),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, 'rb') as f:
                    img = MIMEImage(f.read())
                    img.add_header('Content-ID', '<dormy_logo>')
                    img.add_header('Content-Disposition', 'inline', filename='logo.png')
                    return img
            except Exception as e:
                logger.warning(f"Could not load DORMY logo from {path}: {e}")
                return None
    return None


def send_dormy_branded_email(subject, to_email, html_template, text_template, context=None, fail_silently=False):
    """
    Sends a professional, branded DORMY email with both HTML and plain-text alternatives,
    and automatically embeds the DORMY logo as an inline CID attachment.
    """
    if context is None:
        context = {}

    # Guarantee brand metadata in template context
    context.setdefault('brand_name', getattr(settings, 'DORMY_BRAND_NAME', 'DORMY'))
    context.setdefault('sender_email', getattr(settings, 'DORMY_SENDER_EMAIL', 'joshua.t.jacinto@gmail.com'))
    context.setdefault('timestamp', timezone.now().strftime('%b %d, %Y %I:%M %p UTC'))

    html_content = render_to_string(html_template, context)
    text_content = render_to_string(text_template, context)

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'DORMY <joshua.t.jacinto@gmail.com>')

    message = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=from_email,
        to=[to_email] if isinstance(to_email, str) else to_email,
    )
    message.attach_alternative(html_content, "text/html")

    # Embed DORMY logo via Content-ID (cid:dormy_logo)
    logo_mime = _get_dormy_logo_mime()
    if logo_mime:
        message.attach(logo_mime)

    try:
        sent_count = message.send(fail_silently=fail_silently)
        logger.info(f"DORMY branded email sent to {to_email} with subject: {subject}")
        return sent_count
    except Exception as exc:
        logger.error(f"Failed to send DORMY branded email to {to_email}: {exc}")
        if not fail_silently:
            raise exc
        return 0


def send_registration_otp_email(to_email, otp_code, user_name=None, student_id=None, fail_silently=True):
    """
    Sends the 6-digit registration verification OTP email.
    Notice: 5-minute expiration notice and security reminders included.
    """
    subject = f"{otp_code} is your DORMY registration verification code"
    context = {
        'otp_code': str(otp_code),
        'user_name': user_name,
        'student_id': student_id,
        'timestamp': timezone.now().strftime('%b %d, %Y %I:%M %p UTC'),
    }
    return send_dormy_branded_email(
        subject=subject,
        to_email=to_email,
        html_template='emails/registration_otp.html',
        text_template='emails/registration_otp.txt',
        context=context,
        fail_silently=fail_silently,
    )


def send_login_otp_email(to_email, otp_code, user_name=None, student_id=None, fail_silently=True):
    """
    Sends the 6-digit login authorization OTP email.
    Notice: 5-minute expiration notice and security reminders included.
    """
    subject = f"{otp_code} is your DORMY sign in code"
    context = {
        'otp_code': str(otp_code),
        'user_name': user_name,
        'student_id': student_id,
        'timestamp': timezone.now().strftime('%b %d, %Y %I:%M %p UTC'),
    }
    return send_dormy_branded_email(
        subject=subject,
        to_email=to_email,
        html_template='emails/login_otp.html',
        text_template='emails/login_otp.txt',
        context=context,
        fail_silently=fail_silently,
    )


def send_password_reset_email(to_email, reset_url, otp_code=None, user_name=None, student_id=None, expiry_time=None, fail_silently=True):
    """
    Sends the branded Password Reset email with 6-digit OTP passcode and direct reset link.
    Notice: 15-minute expiration notice and security reminders included.
    """
    if expiry_time is None:
        expiry_dt = timezone.now() + timedelta(minutes=15)
        expiry_time = expiry_dt.strftime('%b %d, %Y %I:%M %p')

    subject = f"{otp_code} is your DORMY password reset code" if otp_code else "Reset Your DORMY Account Password"
    context = {
        'reset_url': reset_url,
        'otp_code': otp_code,
        'user_name': user_name,
        'student_id': student_id,
        'expiry_time': expiry_time,
    }
    return send_dormy_branded_email(
        subject=subject,
        to_email=to_email,
        html_template='emails/password_reset.html',
        text_template='emails/password_reset.txt',
        context=context,
        fail_silently=fail_silently,
    )

