from django.contrib.auth.models import AbstractUser, BaseUserManager, Group, Permission
from django.db import models
from django.conf import settings

# --- 1. USER MANAGER ---
class UserManager(BaseUserManager):
    def create_user(self, student_id, password=None, **extra_fields):
        if not student_id:
            raise ValueError('The Student ID must be set')
        user = self.model(student_id=student_id, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, student_id, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        return self.create_user(student_id, password, **extra_fields)

# --- 2. CUSTOM USER MODEL ---
class User(AbstractUser):
    PAYMENT_STATUS_CHOICES = [
        ('not_paid', 'Not Paid'),
        ('partially_paid', 'Partially Paid'),
        ('fully_paid', 'Fully Paid'),
    ]
    username = None 
    role = models.CharField(
        max_length=10, 
        choices=(('admin', 'Dorm Manager'), ('student', 'Student Resident')), 
        default='student'
    )
    student_id = models.CharField(max_length=20, unique=True, verbose_name="Student ID Number")
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    age = models.IntegerField(null=True, blank=True)
    course = models.CharField(max_length=100, blank=True, null=True)
    year_level = models.IntegerField(null=True, blank=True)
    contact_number = models.CharField(max_length=15, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True, default='profile_pics/default.jpg')
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='not_paid',
        verbose_name="Payment Status"
    )
    
    assigned_room = models.ForeignKey(
        'rooms.Room', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='residents' 
    )

    cleaning_group = models.ForeignKey(
        'scheduling.CleaningGroup',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members'
    )

    groups = models.ManyToManyField(Group, related_name="user_groups", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="user_permissions", blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'student_id'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'email']

    class Meta:
        verbose_name_plural = "Users"

    @property
    def full_name(self):
        """Returns the user's full name."""
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return f"{self.student_id} - {self.full_name}"


# --- 3. EMERGENCY CONTACT MODEL ---
class EmergencyContact(models.Model):
    """
    Stores emergency contact information for a student.
    Each user has a one-to-one relationship with an emergency contact.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='emergency_contact',
        primary_key=True,
    )
    contact_name = models.CharField(max_length=255, verbose_name="Full Name")
    relationship = models.CharField(max_length=100, verbose_name="Relationship")
    phone_number = models.CharField(max_length=20, verbose_name="Phone Number")
    
    class Meta:
        verbose_name = "Emergency Contact"
        verbose_name_plural = "Emergency Contacts"

    def __str__(self):
        return f"Emergency Contact for {self.user.full_name}"


# --- 4. PASSWORD RESET TOKEN ---
import uuid
from django.utils import timezone
from datetime import timedelta

class PasswordResetToken(models.Model):
    """
    One-time secure token and 6-digit OTP for password reset.
    Expires 15 minutes after creation and can only be used once.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='password_reset_tokens',
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    otp_code = models.CharField(max_length=6, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Password Reset Token"
        verbose_name_plural = "Password Reset Tokens"

    def is_valid(self):
        """Returns True if the token is unused and less than 15 minutes old."""
        if self.is_used:
            return False
        return timezone.now() < self.created_at + timedelta(minutes=15)

    def __str__(self):
        return f"Reset token for {self.user.student_id} (OTP: {self.otp_code}, {'used' if self.is_used else 'valid'})"