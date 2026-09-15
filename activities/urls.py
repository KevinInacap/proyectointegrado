from django.urls import path
from . import views

app_name = 'activities'

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('nueva/', views.activity_create_view, name='activity_create'),
    path('actividad/<int:pk>/validar/', views.activity_validate_view, name='activity_validate'),
]

