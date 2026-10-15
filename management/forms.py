from django import forms
from .models import Announcement, Violation, CleaningGroup, CleaningSchedule
from django.contrib.auth import get_user_model

User = get_user_model()

class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ['title', 'content', 'date_posted']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter announcement title'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Enter announcement content'}),
            'date_posted': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default value for date_posted to current datetime
        from django.utils import timezone
        from datetime import datetime
        if not self.instance.pk:  # Only for new instances
            now = timezone.now()
            # Format for datetime-local input: YYYY-MM-DDTHH:MM
            self.fields['date_posted'].initial = now.strftime('%Y-%m-%dT%H:%M')

class ViolationForm(forms.ModelForm):
    student = forms.ModelChoiceField(
        queryset=User.objects.filter(is_staff=False),
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Violation
        fields = ['student', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class PaymentStatusForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['payment_status']
        widgets = {
            'payment_status': forms.Select(attrs={'class': 'form-select form-select-sm'}),
        }

class CleaningGroupForm(forms.ModelForm):
    members = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_staff=False).order_by('first_name', 'last_name'),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = CleaningGroup
        fields = ['name', 'members']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }

class CleaningScheduleForm(forms.ModelForm):
    class Meta:
        model = CleaningSchedule
        fields = ['group', 'day_of_week', 'task']
        widgets = {
            'group': forms.Select(attrs={'class': 'form-control'}),
            'day_of_week': forms.Select(attrs={'class': 'form-control'}),
            'task': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class DormMasterProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

class DormMasterProfilePictureForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['profile_picture']
        widgets = {
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
        }

from rooms.models import Room

class ResidentEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'student_id', 'first_name', 'middle_name', 'last_name',
            'email', 'contact_number', 'course', 'year_level', 'age',
            'assigned_room', 'payment_status', 'is_active', 'profile_picture'
        ]
        widgets = {
            'student_id': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
            'course': forms.TextInput(attrs={'class': 'form-control'}),
            'year_level': forms.NumberInput(attrs={'class': 'form-control'}),
            'age': forms.NumberInput(attrs={'class': 'form-control'}),
            'assigned_room': forms.Select(attrs={'class': 'form-select'}),
            'payment_status': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_room'].queryset = Room.objects.all().order_by('room_number')
        self.fields['assigned_room'].required = False
        self.fields['profile_picture'].required = False