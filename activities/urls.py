from django.urls import path
from . import views

app_name = 'activities'

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard/admin/', views.dashboard_admin_view, name='dashboard_admin'),
    path('dashboard/verificador/', views.dashboard_verificador_view, name='dashboard_verificador'),
    path('dashboard/gestor/', views.dashboard_gestor_view, name='dashboard_gestor'),
    path('nueva/', views.activity_create_view, name='activity_create'),
    path('actividad/<int:pk>/validar/', views.activity_validate_view, name='activity_validate'),
]
