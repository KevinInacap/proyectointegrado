from django.urls import path
from . import views

app_name = 'organization'

urlpatterns = [
    path('users/', views.api_users_list, name='api_users_list'),
    path('users/create/', views.api_user_create, name='api_user_create'),
    path('users/<int:pk>/update/', views.api_user_update, name='api_user_update'),
    path('users/<int:pk>/toggle-status/', views.api_user_toggle_status, name='api_user_toggle_status'),
    path('users/<int:pk>/delete/', views.api_user_delete, name='api_user_delete'),
    path('users/<int:pk>/reset-password/', views.api_user_reset_password, name='api_user_reset_password'),
    path('audit-logs/', views.api_audit_logs, name='api_audit_logs'),
]
