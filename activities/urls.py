from django.urls import path
from . import views

app_name = 'activities'

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard/admin/', views.dashboard_admin_view, name='dashboard_admin'),
    path('dashboard/coordinador/', views.dashboard_coordinador_view, name='dashboard_coordinador'),
    path('dashboard/delegado/', views.dashboard_delegado_view, name='dashboard_delegado'),
    path('dashboard/consulta/', views.dashboard_consulta_view, name='dashboard_consulta'),
    path('dashboard/verificador/', views.dashboard_verificador_view, name='dashboard_verificador'),
    path('dashboard/gestor/', views.dashboard_gestor_view, name='dashboard_gestor'),
    path('nueva/', views.activity_create_view, name='activity_create'),
    path('api/vecinos/', views.api_vecinos, name='api_vecinos_prefixed'),
    path('api/vecinos/<int:pk>/', views.api_vecino_detail, name='api_vecino_detail_prefixed'),
    path('api/atenciones/', views.api_atenciones, name='api_atenciones_prefixed'),
    path('api/atenciones/<int:pk>/', views.api_atencion_detail, name='api_atencion_detail_prefixed'),
    path('api/roles/toggle-permiso/', views.api_toggle_rol_permiso, name='api_toggle_rol_permiso_prefixed'),
    path('vecinos/', views.api_vecinos, name='api_vecinos'),
    path('vecinos/<int:pk>/', views.api_vecino_detail, name='api_vecino_detail'),
    path('atenciones/', views.api_atenciones, name='api_atenciones'),
    path('atenciones/<int:pk>/', views.api_atencion_detail, name='api_atencion_detail'),
    path('roles/toggle-permiso/', views.api_toggle_rol_permiso, name='api_toggle_rol_permiso'),
]
