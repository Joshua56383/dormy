from django.urls import path
from django.views.generic.base import RedirectView
from . import views

app_name = 'management'

urlpatterns = [
    path('', RedirectView.as_view(url='dashboard/', permanent=False), name='management_index'),
    path('dashboard/', views.management_dashboard_view, name='management_dashboard'),
    path('announcements/delete/<int:announcement_id>/', views.delete_announcement_view, name='delete_announcement'),
    path('violations/', views.manage_violations_view, name='manage_violations'),
    path('violations/delete/<int:violation_id>/', views.delete_violation_view, name='delete_violation'),
    path('violations/<int:violation_id>/approve/', views.approve_violation_view, name='approve_violation'),
    path('violations/<int:violation_id>/reject/', views.reject_violation_view, name='reject_violation'),
    path('residents/', views.manage_residents_view, name='manage_residents'),
    path('residents/<int:resident_id>/edit/', views.edit_resident_view, name='edit_resident'),
    path('requests/', views.manage_requests_view, name='manage_requests'),
    path('requests/approve/<int:request_id>/', views.approve_request_view, name='approve_request'),
    path('requests/deny/<int:request_id>/', views.deny_request_view, name='deny_request'),
    path('requests/general/approve/<int:request_id>/', views.approve_general_request_view, name='approve_general_request'),
    path('requests/general/deny/<int:request_id>/', views.deny_general_request_view, name='deny_general_request'),
    path('payments/', views.manage_payments_view, name='manage_payments'),
    path('rooms/', views.manage_rooms_view, name='manage_rooms'),
    path('rooms/<int:room_id>/edit/', views.edit_room_view, name='edit_room'),
    path('rooms/<int:room_id>/delete-photo/', views.delete_room_photo_view, name='delete_room_photo'),
    path('rooms/<int:room_id>/maintenance/', views.set_room_maintenance_view, name='set_room_maintenance'),
    path('account/', views.manage_account_view, name='manage_account'),
    path('cleaning/', views.manage_cleaning_view, name='manage_cleaning'),
]