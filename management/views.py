from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import Announcement, Violation, CleaningGroup, CleaningSchedule, Request
from .forms import AnnouncementForm, ViolationForm, PaymentStatusForm, DormMasterProfileForm, DormMasterProfilePictureForm, CleaningGroupForm, CleaningScheduleForm, ResidentEditForm
from users.models import EmergencyContact
from users.forms import EmergencyContactForm
from django.db.models import Count, Q
from rooms.models import Room, AssignmentRequest, Occupancy
from rooms.forms import RoomForm
from django.contrib.auth import get_user_model

User = get_user_model()

from django.contrib import messages

def is_staff(user):
    return user.is_staff

@login_required
@user_passes_test(is_staff)
def management_dashboard_view(request):
    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save()
            messages.success(request, f'Announcement "{announcement.title}" has been posted successfully.')
            return redirect('management:management_dashboard')
        else:
            messages.error(request, 'Could not post announcement. Please check the form for errors.')
    else:
        form = AnnouncementForm()

    # Fetch all the counts for the dashboard stats
    announcements = Announcement.objects.all().order_by('-date_posted')
    total_residents = User.objects.filter(is_staff=False).count()
    violations_count = Violation.objects.count()
    rooms_count = Room.objects.count()
    pending_payments_count = User.objects.filter(is_staff=False).exclude(payment_status='paid').count()

    context = {
        'form': form,
        'announcements': announcements,
        'total_residents': total_residents,
        'violations_count': violations_count,
        'rooms_count': rooms_count,
        'pending_payments_count': pending_payments_count,
    }
    return render(request, 'mdashboard.html', context)

@login_required
@user_passes_test(is_staff)
def delete_announcement_view(request, announcement_id):
    announcement = get_object_or_404(Announcement, id=announcement_id)
    announcement.delete()
    messages.success(request, f'Announcement "{announcement.title}" has been deleted.')
    return redirect('management:management_dashboard')


@login_required
@user_passes_test(is_staff)
def manage_violations_view(request):
    if request.method == 'POST':
        form = ViolationForm(request.POST)
        if form.is_valid():
            violation = form.save(commit=False)
            # Staff-logged violations are pre-approved (no review needed)
            violation.status = 'approved'
            violation.reviewed_by = request.user
            violation.save()
            messages.success(request, f'Violation has been recorded for {violation.student.full_name}.')
            return redirect('management:manage_violations')
    else:
        form = ViolationForm()

    # Confirmed violations (approved)
    violations = Violation.objects.filter(status='approved').order_by('-date_committed')
    # Pending student reports awaiting review
    pending_reports = Violation.objects.filter(status='pending').order_by('-date_committed')
    all_students = User.objects.filter(is_staff=False)
    context = {
        'form': form,
        'violations': violations,
        'pending_reports': pending_reports,
        'all_students': all_students,
    }
    return render(request, 'manage_violations.html', context)

@login_required
@user_passes_test(is_staff)
def approve_violation_view(request, violation_id):
    """Dorm master approves a student-submitted violation report."""
    violation = get_object_or_404(Violation, id=violation_id)
    if request.method == 'POST':
        violation.status = 'approved'
        violation.reviewed_by = request.user
        violation.review_note = request.POST.get('review_note', '').strip()
        violation.save()
        messages.success(request, f"Violation report for {violation.student.full_name} has been approved and recorded.")
    return redirect('management:manage_violations')

@login_required
@user_passes_test(is_staff)
def reject_violation_view(request, violation_id):
    """Dorm master rejects / dismisses a student-submitted violation report."""
    violation = get_object_or_404(Violation, id=violation_id)
    if request.method == 'POST':
        violation.status = 'rejected'
        violation.reviewed_by = request.user
        violation.review_note = request.POST.get('review_note', '').strip()
        violation.save()
        messages.info(request, f"Violation report for {violation.student.full_name} has been rejected.")
    return redirect('management:manage_violations')


@login_required
@user_passes_test(is_staff)
def delete_violation_view(request, violation_id):
    violation = get_object_or_404(Violation, id=violation_id)
    student_name = violation.student.full_name
    violation.delete()
    messages.success(request, f"The violation for {student_name} has been successfully deleted.")
    return redirect('management:manage_violations')

@login_required
@user_passes_test(is_staff)
def manage_payments_view(request):
    students = User.objects.filter(is_staff=False).order_by('last_name')
    student_forms = {student.id: PaymentStatusForm(instance=student) for student in students}

    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        try:
            student = User.objects.get(id=student_id)
            form = PaymentStatusForm(request.POST, instance=student)
            if form.is_valid():
                form.save()
                student.refresh_from_db()
                messages.success(request, f"Payment status for {student.full_name} has been updated to {student.get_payment_status_display()}.")
                return redirect('management:manage_payments')
            else:
                student_forms[student.id] = form
                messages.error(request, f'Could not update for {student.full_name}. Please correct the error.')
        except User.DoesNotExist:
            messages.error(request, 'Student not found.')

    context = {
        'students_with_forms': [(student, student_forms[student.id]) for student in students],
    }
    return render(request, 'manage_payments.html', context)

@login_required
@user_passes_test(is_staff)
def manage_rooms_view(request):
    if request.method == 'POST':
        form = RoomForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Room has been created successfully.')
            return redirect('management:manage_rooms')
    else:
        form = RoomForm()

    rooms = Room.objects.all()
    context = {
        'form': form,
        'rooms': rooms,
    }
    return render(request, 'manage_rooms.html', context)


@login_required
@user_passes_test(is_staff)
def edit_room_view(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    if request.method == 'POST':
        form = RoomForm(request.POST, request.FILES, instance=room)
        if form.is_valid():
            form.save()
            messages.success(request, f'Room {room.room_number} has been updated successfully.')
            return redirect('management:edit_room', room_id=room.id)
    else:
        form = RoomForm(instance=room)
    context = {
        'form': form,
        'room': room,
    }
    return render(request, 'edit_room.html', context)


@login_required
@user_passes_test(is_staff)
def delete_room_photo_view(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    if room.photo:
        room.photo.delete(save=False)
    room.photo = None
    room.save()
    messages.success(request, f'Photo for Room {room.room_number} has been deleted.')
    return redirect('management:edit_room', room_id=room.id)

@login_required
@user_passes_test(is_staff)
def set_room_maintenance_view(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    if room.status == 'maintenance':
        room.status = 'available'
        messages.success(request, f'Room {room.room_number} is now available.')
    else:
        room.status = 'maintenance'
        messages.success(request, f'Room {room.room_number} is now under maintenance.')
    room.save()
    return redirect('management:manage_rooms')

@login_required
@user_passes_test(is_staff)
def manage_residents_view(request):
    residents = User.objects.filter(is_staff=False).select_related('assigned_room').order_by('last_name', 'first_name')
    context = {
        'residents': residents,
    }
    return render(request, 'manage_residents.html', context)

@login_required
@user_passes_test(is_staff)
def edit_resident_view(request, resident_id):
    resident = get_object_or_404(User, id=resident_id, is_staff=False)
    emergency_contact, _ = EmergencyContact.objects.get_or_create(user=resident)

    if request.method == 'POST':
        resident_form = ResidentEditForm(request.POST, request.FILES, instance=resident)
        emergency_form = EmergencyContactForm(request.POST, instance=emergency_contact)
        if resident_form.is_valid() and emergency_form.is_valid():
            resident_form.save()
            emergency_form.save()
            messages.success(request, f'Resident profile for {resident.full_name} has been updated successfully.')
            return redirect('management:manage_residents')
        else:
            messages.error(request, 'Please correct the errors in the form.')
    else:
        resident_form = ResidentEditForm(instance=resident)
        emergency_form = EmergencyContactForm(instance=emergency_contact)

    context = {
        'resident': resident,
        'resident_form': resident_form,
        'emergency_form': emergency_form,
    }
    return render(request, 'edit_resident.html', context)


@login_required
@user_passes_test(is_staff)
def manage_requests_view(request):
    assignment_requests = AssignmentRequest.objects.filter(status='pending').select_related('student', 'room')
    general_requests = Request.objects.filter(status='pending').select_related('student')
    context = {
        'assignment_requests': assignment_requests,
        'general_requests': general_requests,
    }
    return render(request, 'manage_requests.html', context)

@login_required
@user_passes_test(is_staff)
def approve_request_view(request, request_id):
    assignment_request = get_object_or_404(AssignmentRequest, id=request_id)
    student = assignment_request.student
    room = assignment_request.room

    if room.is_full:
        messages.error(request, f"Could not approve request. Room {room.room_number} is already full.")
        assignment_request.status = 'denied'
        assignment_request.save()
    else:
        # If the student is already in a room, we must handle the transfer by deleting the old occupancy record.
        try:
            old_occupancy = Occupancy.objects.get(student=student)
            old_room = old_occupancy.room
            old_occupancy.delete() # Correctly vacate the old room.
            old_room.save() # Trigger a status update on the old room.
        except Occupancy.DoesNotExist:
            # This is a new assignment, not a transfer. No old room to vacate.
            pass

        # Assign the student to the new room by creating a new Occupancy record.
        Occupancy.objects.create(student=student, room=room)

        # Update the student's main room assignment to keep all records in sync.
        student.assigned_room = room
        student.save()

        assignment_request.status = 'approved'
        assignment_request.save()

        # Deny other pending requests from the same student.
        AssignmentRequest.objects.filter(student=student, status='pending').update(status='denied')

        room.save() # Trigger a status update on the new room.
        messages.success(request, f"{student.full_name} has been assigned to Room {room.room_number}.")

    return redirect('management:manage_requests')

@login_required
@user_passes_test(is_staff)
def approve_general_request_view(request, request_id):
    general_request = get_object_or_404(Request, id=request_id)
    general_request.status = 'approved'
    general_request.save()
    messages.success(request, f"Request from {general_request.student.full_name} has been approved.")
    return redirect('management:manage_requests')

@login_required
@user_passes_test(is_staff)
def deny_general_request_view(request, request_id):
    general_request = get_object_or_404(Request, id=request_id)
    general_request.status = 'denied'
    general_request.save()
    messages.info(request, f"Request from {general_request.student.full_name} has been denied.")
    return redirect('management:manage_requests')

@login_required
@user_passes_test(is_staff)
def deny_request_view(request, request_id):
    assignment_request = get_object_or_404(AssignmentRequest, id=request_id)
    assignment_request.status = 'denied'
    assignment_request.save()
    messages.info(request, f"Request for {assignment_request.student.full_name} has been denied.")
    return redirect('management:manage_requests')

@login_required
@user_passes_test(is_staff)
def manage_account_view(request):
    return redirect('management:management_dashboard')

@login_required
@user_passes_test(is_staff)
def manage_cleaning_view(request):
    # Handle Group Creation/Update
    if request.method == 'POST' and 'manage_group' in request.POST:
        group_id = request.POST.get('group_id')
        group = get_object_or_404(CleaningGroup, id=group_id) if group_id else None
        group_form = CleaningGroupForm(request.POST, instance=group)
        if group_form.is_valid():
            group_form.save()
            messages.success(request, f"Group '{group_form.instance.name}' has been saved.")
            return redirect('management:manage_cleaning')

    # Handle Schedule Creation/Update
    if request.method == 'POST' and 'manage_schedule' in request.POST:
        schedule_form = CleaningScheduleForm(request.POST)
        if schedule_form.is_valid():
            schedule_form.save()
            messages.success(request, "The schedule has been saved.")
            return redirect('management:manage_cleaning')

    # Handle Deletions
    if request.method == 'POST' and 'delete_group' in request.POST:
        group_id = request.POST.get('group_id')
        CleaningGroup.objects.filter(id=group_id).delete()
        messages.success(request, "The group has been deleted.")
        return redirect('management:manage_cleaning')

    if request.method == 'POST' and 'delete_schedule' in request.POST:
        schedule_id = request.POST.get('schedule_id')
        CleaningSchedule.objects.filter(id=schedule_id).delete()
        messages.success(request, "The schedule has been deleted.")
        return redirect('management:manage_cleaning')

    group_form = CleaningGroupForm()
    schedule_form = CleaningScheduleForm()
    groups = CleaningGroup.objects.prefetch_related('members', 'schedules').all()
    schedules_by_day = {day: [] for day, _ in CleaningSchedule.DAYS_OF_WEEK}
    for schedule in CleaningSchedule.objects.select_related('group').all():
        schedules_by_day[schedule.day_of_week].append(schedule)

    all_students = User.objects.filter(is_staff=False)

    context = {
        'group_form': group_form,
        'schedule_form': schedule_form,
        'groups': groups,
        'schedules_by_day': schedules_by_day,
        'days_of_week': CleaningSchedule.DAYS_OF_WEEK,
        'all_students': all_students,
    }
    return render(request, 'manage_cleaning.html', context)