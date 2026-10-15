from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.decorators import login_required
from .forms import (
    RegistrationForm,
    UserProfileForm,
    EmergencyContactForm,
    RequestForm,
    StudentViolationReportForm,
    UnifiedAccountSettingsForm,
    ForgotPasswordForm,
    ResetPasswordForm,
    OTPVerificationForm,
)
from .models import User, EmergencyContact, PasswordResetToken
from .emails import send_password_reset_email
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
import secrets
import logging

logger = logging.getLogger(__name__)

# Import models from other apps
from management.models import Announcement as ManagementAnnouncement, Violation, CleaningSchedule
from scheduling.models import Announcement
from rooms.models import Room, Occupancy

User = get_user_model()

from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def toggle_resident_status(request, user_id):
    if request.method == 'POST':
        resident = get_object_or_404(User, id=user_id)
        resident.is_active = not resident.is_active
        resident.save()
        messages.success(request, f"{resident.full_name}'s account has been {'activated' if resident.is_active else 'deactivated'}.")
    return redirect('management:manage_residents')

# --- 1. REGISTRATION VIEW ---
def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.is_active = False  # Admin approval required
            user.save()
            room = form.cleaned_data.get('room')
            if room:
                from rooms.models import Occupancy
                Occupancy.objects.create(student=user, room=room)
                user.assigned_room = room
                user.save()
            messages.success(request, "Registration successful! Please wait for admin approval.")
            return redirect('users:login')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = RegistrationForm()
    return render(request, 'register.html', {'form': form})

# --- 2. LOGIN VIEW ---
def login_view(request):
    next_url = request.POST.get('next') or request.GET.get('next')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)

            if user is not None:
                if user.is_active:
                    login(request, user)
                    if user.is_staff:
                        return redirect('management:management_dashboard')
                    elif next_url and url_has_allowed_host_and_scheme(
                        next_url,
                        allowed_hosts={request.get_host()},
                        require_https=request.is_secure(),
                    ):
                        return redirect(next_url)
                    else:
                        return redirect('users:dashboard')
                else:
                    messages.error(request, "Your account is not active.")
            else:
                messages.error(request, "Invalid credentials.")
        else:
            messages.error(request, "Invalid credentials or account not yet active.")
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form, 'request': request, 'next': next_url})

# --- 3. LOGOUT VIEW ---
def logout_view(request):
    logout(request)
    messages.info(request, "You have logged out.")
    return redirect('users:login')

# --- 4. DASHBOARD VIEW ---
from rooms.models import Occupancy # Source of Truth for Rooms
from scheduling.models import Announcement # Source of Truth for News
from django.contrib.auth import get_user_model

User = get_user_model()

@login_required
def dashboard_view(request):
    current_user = request.user
    display_room = None
    display_roommates = []

    request_form = RequestForm()
    violation_form = StudentViolationReportForm(current_user=current_user)

    if request.method == 'POST':
        if 'submit_violation' in request.POST:
            violation_form = StudentViolationReportForm(request.POST, current_user=current_user)
            if violation_form.is_valid():
                violation = violation_form.save(commit=False)
                violation.reported_by = current_user
                violation.status = 'pending'  # Student reports need dorm-master approval
                violation.save()
                messages.success(request, f"Violation report for {violation.student.full_name} has been submitted to dorm management for review.")
                return redirect('users:dashboard')
            else:
                messages.error(request, "Could not submit violation report. Please check the fields.")
        else:
            request_form = RequestForm(request.POST)
            if request_form.is_valid():
                new_request = request_form.save(commit=False)
                new_request.student = current_user
                new_request.save()
                messages.success(request, "Your request has been submitted successfully.")
                return redirect('users:dashboard')

    # 1. FETCH ROOM using the relationship on the user model
    if hasattr(current_user, 'room_assignment') and current_user.room_assignment:
        display_room = current_user.room_assignment.room
    else:
        display_room = None

    # 2. FETCH ROOMMATES using the relationship on the room model
    if display_room:
        display_roommates = display_room.residents.exclude(id=current_user.id)

    # 3. FETCH ANNOUNCEMENTS (from the management app)
    all_announcements = ManagementAnnouncement.objects.all().order_by('-date_posted')

    # 4. FETCH VIOLATIONS for the current user
    user_violations = Violation.objects.filter(student=current_user).order_by('-date_committed')

    # 5. FETCH VIOLATIONS REPORTED BY the current user
    reported_by_user = Violation.objects.filter(reported_by=current_user).order_by('-date_committed')

    # 6. GET PAYMENT STATUS
    payment_status = current_user.get_payment_status_display()

    # 7. GET USER REQUESTS
    user_requests = current_user.requests.all().order_by('-date_submitted')

    context = {
        'display_room': display_room,
        'display_roommates': display_roommates,
        'announcements': all_announcements,
        'user_violations': user_violations,
        'reported_by_user': reported_by_user,
        'payment_status': payment_status,
        'request_form': request_form,
        'violation_form': violation_form,
        'user_requests': user_requests,
    }
    return render(request, 'dashboard.html', context)

@login_required
def report_violation_view(request):
    current_user = request.user
    if request.method == 'POST':
        form = StudentViolationReportForm(request.POST, current_user=current_user)
        if form.is_valid():
            violation = form.save(commit=False)
            violation.reported_by = current_user
            violation.status = 'pending'  # Await dorm-master review
            violation.save()
            messages.success(request, f"Your violation report for {violation.student.full_name} has been submitted. The dorm master will review it shortly.")
            return redirect('users:report_violation')
        else:
            messages.error(request, "Please check the form for errors.")
    else:
        form = StudentViolationReportForm(current_user=current_user)

    reported_history = Violation.objects.filter(reported_by=current_user).order_by('-date_committed')
    context = {
        'form': form,
        'reported_history': reported_history,
    }
    return render(request, 'report_violation.html', context)


@login_required
def schedule_view(request):
    """
    This view prepares the data for the schedule page, including cleaning schedules
    and announcements.
    """
    schedules_by_day = {day: [] for day, _ in CleaningSchedule.DAYS_OF_WEEK}
    schedules = CleaningSchedule.objects.select_related('group').prefetch_related('group__members').all()
    
    # Group schedules in Python to preserve the pre-fetched member data
    for schedule in schedules:
        schedules_by_day[schedule.day_of_week].append(schedule)

    # Fetch all announcements from the management app
    announcements = ManagementAnnouncement.objects.order_by('-date_posted')
    
    context = {
        'schedules_by_day': schedules_by_day,
        'announcements': announcements,
        'total_schedules': schedules.count(),
    }
    
    return render(request, 'schedule.html', context)

# --- 6. RULES VIEW ---
@login_required
def rules_view(request):
    return render(request, 'rules.html')


# --- 5. ACCOUNT SETTINGS VIEW ---
@login_required
def account_view(request):
    user = request.user

    if request.method == 'POST':
        form = UnifiedAccountSettingsForm(request.POST, request.FILES, user=user)
        if form.is_valid():
            user, password_changed = form.save()
            if password_changed:
                update_session_auth_hash(request, user)
                messages.success(request, 'Your account settings and password have been successfully updated!')
            else:
                messages.success(request, 'Your account settings have been successfully updated!')
        else:
            # Collect all field errors into a single readable message
            error_parts = []
            for field, errs in form.errors.items():
                label = field.replace('_', ' ').capitalize()
                for err in errs:
                    error_parts.append(f"{label}: {err}")
            error_text = ' | '.join(error_parts) if error_parts else 'Please check the form for errors.'
            # Use special tag 'account_settings_error' so the JS can re-open the modal
            messages.error(request, f"Could not save — {error_text}", extra_tags='account_settings_error')

        next_url = request.POST.get('next')
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)
        return redirect('users:dashboard')

    # If accessed directly via GET, redirect back to referer or dashboard
    next_url = request.GET.get('next') or request.META.get('HTTP_REFERER') or 'users:dashboard'
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect('users:dashboard')


# --- 7. FORGOT & RESET PASSWORD VIEWS (WITH 6-DIGIT OTP) ---
def mask_email(email):
    if not email:
        return ""
    if '@' in email:
        parts = email.split('@')
        if len(parts[0]) > 2:
            masked = parts[0][0] + '***' + parts[0][-1]
        else:
            masked = parts[0][0] + '***'
        return f"{masked}@{parts[1]}"
    return email


def forgot_password_view(request):
    if request.user.is_authenticated:
        return redirect('users:dashboard')

    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            user = form.user_obj
            # Invalidate previous unused tokens for security
            PasswordResetToken.objects.filter(user=user, is_used=False).update(is_used=True)

            # Generate fresh 6-digit numeric OTP and secure token
            otp_code = f"{secrets.randbelow(900000) + 100000}"
            token = PasswordResetToken.objects.create(user=user, otp_code=otp_code)
            reset_url = request.build_absolute_uri(
                reverse('users:reset_password', kwargs={'token': token.token})
            )

            expiry_dt = token.created_at + timedelta(minutes=15)
            expiry_str = expiry_dt.strftime('%b %d, %Y %I:%M %p')

            try:
                send_password_reset_email(
                    to_email=user.email,
                    reset_url=reset_url,
                    otp_code=otp_code,
                    user_name=user.full_name,
                    student_id=user.student_id,
                    expiry_time=expiry_str,
                    fail_silently=False
                )
            except Exception as e:
                logger.error(f"Error sending password reset email: {e}")

            logger.info("=" * 50)
            logger.info(f"[DORMY OTP] Student ID: {user.student_id} | Email: {user.email}")
            logger.info(f"[DORMY OTP CODE]: {otp_code}")
            logger.info("=" * 50)

            messages.success(request, f"A 6-digit verification code has been sent to {mask_email(user.email)}.")
            return redirect('users:verify_otp', token=token.token)
    else:
        form = ForgotPasswordForm()

    return render(request, 'forgot_password.html', {'form': form})


def verify_otp_view(request, token):
    if request.user.is_authenticated:
        return redirect('users:dashboard')

    reset_token = PasswordResetToken.objects.filter(token=token).first()
    if not reset_token or not reset_token.is_valid():
        return render(request, 'verify_otp.html', {
            'is_invalid': True,
        })

    user = reset_token.user
    masked = mask_email(user.email)
    error_msg = None

    if request.method == 'POST':
        # Accept either individual 6 digit fields (digit_1 to digit_6) or a single combined otp_code
        digits = [request.POST.get(f'digit_{i}', '').strip() for i in range(1, 7)]
        combined = "".join(digits)
        code = combined or request.POST.get('otp_code', '').strip()

        if code and code == reset_token.otp_code:
            request.session[f'otp_verified_{reset_token.token}'] = True
            messages.success(request, "Code verified successfully! You may now set your new password.")
            return redirect('users:reset_password', token=reset_token.token)
        else:
            error_msg = "Invalid verification code. Please check the 6 digits and try again."

    return render(request, 'verify_otp.html', {
        'reset_token': reset_token,
        'target_user': user,
        'masked_email': masked,
        'error_msg': error_msg,
        'is_invalid': False,
    })


def resend_otp_view(request, token):
    if request.user.is_authenticated:
        return redirect('users:dashboard')

    reset_token = PasswordResetToken.objects.filter(token=token, is_used=False).first()
    if not reset_token:
        messages.error(request, "Invalid or expired session. Please request a new password reset.")
        return redirect('users:forgot_password')

    user = reset_token.user
    new_otp = f"{secrets.randbelow(900000) + 100000}"
    reset_token.otp_code = new_otp
    reset_token.created_at = timezone.now()
    reset_token.save()

    reset_url = request.build_absolute_uri(
        reverse('users:reset_password', kwargs={'token': reset_token.token})
    )
    expiry_dt = reset_token.created_at + timedelta(minutes=15)
    expiry_str = expiry_dt.strftime('%b %d, %Y %I:%M %p')

    try:
        send_password_reset_email(
            to_email=user.email,
            reset_url=reset_url,
            otp_code=new_otp,
            user_name=user.full_name,
            student_id=user.student_id,
            expiry_time=expiry_str,
            fail_silently=False
        )
    except Exception as e:
        logger.error(f"Error resending password reset email: {e}")

    logger.info("=" * 50)
    logger.info(f"[DORMY OTP RESENT] Student ID: {user.student_id} | Email: {user.email}")
    logger.info(f"[DORMY OTP CODE]: {new_otp}")
    logger.info("=" * 50)

    messages.success(request, f"A fresh 6-digit verification code has been dispatched to {mask_email(user.email)}.")
    return redirect('users:verify_otp', token=reset_token.token)


def reset_password_view(request, token):
    if request.user.is_authenticated:
        return redirect('users:dashboard')

    reset_token = PasswordResetToken.objects.filter(token=token).first()

    if not reset_token or not reset_token.is_valid():
        return render(request, 'reset_password.html', {
            'is_invalid': True,
        })

    user = reset_token.user

    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            user.set_password(new_password)
            user.save()

            # Mark token used
            reset_token.is_used = True
            reset_token.save()
            request.session.pop(f'otp_verified_{reset_token.token}', None)

            messages.success(request, "Your password has been successfully reset! You can now sign in with your new password.")
            return redirect('users:login')
    else:
        form = ResetPasswordForm()

    return render(request, 'reset_password.html', {
        'form': form,
        'is_invalid': False,
        'target_user': user,
        'token': token,
    })