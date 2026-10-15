from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UserChangeForm as BaseUserChangeForm

from .models import User, EmergencyContact
from management.models import Request
from rooms.models import Room


class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    room = forms.ModelChoiceField(
        queryset=Room.objects.filter(status='available'),
        empty_label='Select a room',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['student_id', 'first_name', 'middle_name', 'last_name', 'email', 'course', 'year_level', 'contact_number', 'password']
        widgets = {
            'student_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 2024-0001'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'course': forms.TextInput(attrs={'class': 'form-control'}),
            'year_level': forms.NumberInput(attrs={'class': 'form-control'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter to rooms that actually have space
        self.fields['room'].queryset = Room.objects.filter(status='available').order_by('room_number')


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        # Users can only edit these specific fields
        fields = ['profile_picture', 'email', 'contact_number']
        widgets = {
            'profile_picture': forms.FileInput(attrs={'class': 'form-control mb-2'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)
        self.fields['profile_picture'].required = False


class UnifiedAccountSettingsForm(forms.Form):
    # --- 1. Profile & Identity ---
    first_name = forms.CharField(
        required=True,
        max_length=100,
        label="First Name",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        required=True,
        max_length=100,
        label="Last Name",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    profile_picture = forms.ImageField(
        required=False,
        label="Profile Picture",
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        required=True,
        label="Email Address",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@example.com'})
    )
    contact_number = forms.CharField(
        required=False,
        max_length=15,
        label="Contact Number",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 09123456789'})
    )

    # --- 2. Emergency Contact ---
    contact_name = forms.CharField(
        required=False,
        max_length=255,
        label="Emergency Contact Name",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name of guardian / contact'})
    )
    relationship = forms.CharField(
        required=False,
        max_length=100,
        label="Relationship",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Mother, Father, Guardian'})
    )
    phone_number = forms.CharField(
        required=False,
        max_length=20,
        label="Emergency Contact Phone",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 09987654321'})
    )

    # --- 3. Optional Password Change ---
    current_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Required only if changing password'}),
        label="Current Password"
    )
    new_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New password (min 6 characters)'}),
        label="New Password"
    )
    confirm_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new password'}),
        label="Confirm New Password"
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['email'].initial = self.user.email
            self.fields['contact_number'].initial = self.user.contact_number
            try:
                contact = self.user.emergency_contact
                if contact:
                    self.fields['contact_name'].initial = contact.contact_name
                    self.fields['relationship'].initial = contact.relationship
                    self.fields['phone_number'].initial = contact.phone_number
            except Exception:
                pass

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Email is not unique in the model — just return it as-is.
        return email

    def clean(self):
        cleaned_data = super().clean()
        curr_p = cleaned_data.get('current_password')
        new_p = cleaned_data.get('new_password')
        conf_p = cleaned_data.get('confirm_password')

        # If any password field is entered, validate password change requirements
        if curr_p or new_p or conf_p:
            if not curr_p:
                self.add_error('current_password', "Please enter your current password to authorize changing it.")
            elif not self.user.check_password(curr_p):
                self.add_error('current_password', "Current password is incorrect.")

            if not new_p:
                self.add_error('new_password', "Please enter a new password.")
            elif len(new_p) < 6:
                self.add_error('new_password', "New password must be at least 6 characters long.")

            if not conf_p:
                self.add_error('confirm_password', "Please confirm your new password.")
            elif new_p and conf_p and new_p != conf_p:
                self.add_error('confirm_password', "New passwords do not match.")

        return cleaned_data

    def save(self):
        if not self.user:
            return None, False
        cd = self.cleaned_data

        # Update User model
        self.user.first_name = cd['first_name']
        self.user.last_name = cd['last_name']
        self.user.email = cd['email']
        self.user.contact_number = cd.get('contact_number', '')
        if cd.get('profile_picture'):
            self.user.profile_picture = cd['profile_picture']

        password_changed = False
        if cd.get('new_password'):
            self.user.set_password(cd['new_password'])
            password_changed = True

        self.user.save()

        # Update or create Emergency Contact
        c_name = cd.get('contact_name', '').strip()
        c_rel = cd.get('relationship', '').strip()
        c_phone = cd.get('phone_number', '').strip()

        if c_name or c_rel or c_phone:
            EmergencyContact.objects.update_or_create(
                user=self.user,
                defaults={
                    'contact_name': c_name,
                    'relationship': c_rel,
                    'phone_number': c_phone,
                }
            )

        return self.user, password_changed


class CustomUserCreationForm(UserCreationForm):
    """A form for creating new users in the admin, with no privileges."""

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ('student_id', 'first_name', 'middle_name', 'last_name', 'email')


class CustomUserChangeForm(BaseUserChangeForm):
    """A form for updating users in the admin. Includes all fields."""

    class Meta(BaseUserChangeForm.Meta):
        model = get_user_model()
        fields = '__all__'


class EmergencyContactForm(forms.ModelForm):
    class Meta:
        model = EmergencyContact
        fields = ['contact_name', 'relationship', 'phone_number']
        widgets = {
            'contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'relationship': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Mother, Father, Guardian'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

class RequestForm(forms.ModelForm):
    class Meta:
        model = Request
        fields = ['request_type', 'description']
        widgets = {
            'request_type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Please provide details about your request.'}),
        }

from management.models import Violation

class StudentViolationReportForm(forms.ModelForm):
    student = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label="Resident Involved",
        empty_label="Select Resident",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Violation
        fields = ['student', 'description']
        widgets = {
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe the incident or infraction (e.g. noise during quiet hours, unauthorized guests, cleanliness, damage)...'
            }),
        }

    def __init__(self, *args, **kwargs):
        current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)
        qs = User.objects.filter(is_staff=False)
        if current_user:
            qs = qs.exclude(id=current_user.id)
        self.fields['student'].queryset = qs.order_by('first_name', 'last_name')


class ForgotPasswordForm(forms.Form):
    identifier = forms.CharField(
        max_length=150,
        required=True,
        label="Student ID or Email Address",
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'e.g. 2024-00123 or your.email@example.com',
            'autocomplete': 'username',
            'autofocus': True,
        })
    )

    def clean_identifier(self):
        val = self.cleaned_data.get('identifier', '').strip()
        if not val:
            raise forms.ValidationError("Please enter your Student ID or registered email address.")
        
        # Search by student_id or email
        user = User.objects.filter(student_id__iexact=val).first()
        if not user:
            user = User.objects.filter(email__iexact=val).first()

        if not user:
            raise forms.ValidationError("We could not find an account associated with that Student ID or email.")

        if not user.email:
            raise forms.ValidationError("This account does not have a registered email address. Please contact your Dorm Master.")

        self.user_obj = user
        return val


class ResetPasswordForm(forms.Form):
    new_password = forms.CharField(
        required=True,
        min_length=6,
        label="New Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter new password (min. 6 characters)',
            'autocomplete': 'new-password',
            'autofocus': True,
        })
    )
    confirm_password = forms.CharField(
        required=True,
        min_length=6,
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Confirm your new password',
            'autocomplete': 'new-password',
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('new_password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_password', "Passwords do not match. Please re-enter.")
        return cleaned_data


class OTPVerificationForm(forms.Form):
    otp_code = forms.CharField(
        min_length=6,
        max_length=6,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg text-center fw-bold letter-spacing-lg',
            'placeholder': '••••••',
            'maxlength': '6',
            'inputmode': 'numeric',
            'pattern': '[0-9]*',
            'autocomplete': 'one-time-code',
            'autofocus': True,
        })
    )

    def clean_otp_code(self):
        val = self.cleaned_data.get('otp_code', '').strip()
        if not val.isdigit() or len(val) != 6:
            raise forms.ValidationError("Please enter a valid 6-digit verification code.")
        return val
