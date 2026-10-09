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
    path('delegations/', views.api_delegations, name='api_delegations'),
    path('delegations/<int:pk>/update/', views.api_delegation_update, name='api_delegation_update'),
    path('delegations/<int:pk>/toggle-status/', views.api_delegation_toggle, name='api_delegation_toggle'),
    path('positions/', views.api_positions, name='api_positions'),
    path('positions/<int:pk>/update/', views.api_position_update, name='api_position_update'),
    path('positions/<int:pk>/toggle-status/', views.api_position_toggle, name='api_position_toggle'),
    
    # Roles & Permisos (RBAC MyAdmin)
    path('roles/', views.api_roles_list, name='api_roles_list'),
    path('roles/create/', views.api_role_create, name='api_role_create'),
    path('roles/<int:pk>/update/', views.api_role_update, name='api_role_update'),
    path('roles/<int:pk>/delete/', views.api_role_delete, name='api_role_delete'),
    path('roles/<int:pk>/duplicate/', views.api_role_duplicate, name='api_role_duplicate'),
    path('roles/permissions/catalog/', views.api_permissions_catalog, name='api_permissions_catalog'),
    path('roles/permissions/add-custom/', views.api_add_custom_permission, name='api_add_custom_permission'),
]
