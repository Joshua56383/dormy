from django.urls import path
from . import views
from rooms.views import available_rooms_view

app_name = 'users'

urlpatterns = [
    path('', available_rooms_view, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('schedule/', views.schedule_view, name='schedule'),
    path('rules/', views.rules_view, name='rules'),
    path('violations/report/', views.report_violation_view, name='report_violation'),
    path('account/', views.account_view, name='account'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('verify-otp/<uuid:token>/', views.verify_otp_view, name='verify_otp'),
    path('resend-otp/<uuid:token>/', views.resend_otp_view, name='resend_otp'),
    path('reset-password/<uuid:token>/', views.reset_password_view, name='reset_password'),
    path('residents/toggle-status/<int:user_id>/', views.toggle_resident_status, name='toggle_resident_status'),
]