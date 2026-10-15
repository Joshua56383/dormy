from django.db import models
from django.utils import timezone
from django.conf import settings

class Announcement(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    event_date = models.DateTimeField(null=True, blank=True)
    date_posted = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title

class Violation(models.Model):
    STATUS_PENDING  = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'

    STATUS_CHOICES = [
        (STATUS_PENDING,  'Pending Review'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='management_violations')
    description = models.TextField()
    date_committed = models.DateTimeField(default=timezone.now)
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reported_violations')
    # 'pending'  = submitted by a student, awaiting dorm-master review
    # 'approved' = confirmed by dorm master (or logged directly by staff)
    # 'rejected' = dorm master dismissed the report
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_APPROVED)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_violations')
    review_note = models.TextField(blank=True, default='')

    @property
    def is_student_report(self):
        """True when a non-staff resident submitted this report."""
        return self.reported_by is not None and not self.reported_by.is_staff

    def __str__(self):
        return f"Violation for {self.student} on {self.date_committed.strftime('%Y-%m-%d')} [{self.get_status_display()}]"


class CleaningGroup(models.Model):
    name = models.CharField(max_length=100, unique=True)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='cleaning_groups', limit_choices_to={'is_staff': False})

    def __str__(self):
        return self.name

class CleaningSchedule(models.Model):
    DAYS_OF_WEEK = [
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday'),
    ]
    group = models.ForeignKey(CleaningGroup, on_delete=models.CASCADE, related_name='schedules')
    day_of_week = models.CharField(max_length=10, choices=DAYS_OF_WEEK)
    task = models.TextField()

    def __str__(self):
        return f"{self.group.name} - {self.day_of_week}"

class Request(models.Model):
    REQUEST_TYPES = (
        ('maintenance', 'Maintenance'),
        ('stay_out', 'Stay Out Overnight'),
        ('other', 'Other'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
    )

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='requests')
    request_type = models.CharField(max_length=20, choices=REQUEST_TYPES)
    description = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    date_submitted = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Request from {self.student} ({self.get_request_type_display()})"