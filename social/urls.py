from django.urls import path
from . import views

app_name = 'social'

urlpatterns = [
    path('dashboard/', views.dashboard_asistente_view, name='dashboard_asistente'),
    path('api/casos/', views.api_casos_sociales, name='api_casos'),
    path('api/casos/<int:pk>/', views.api_caso_detalle, name='api_caso_detalle'),
    path('api/casos/<int:pk>/avanzar-etapa/', views.api_avanzar_etapa, name='api_avanzar_etapa'),
    path('api/casos/<int:pk>/solicitudes/', views.api_solicitud_caso, name='api_solicitud_caso'),
    path('api/casos/<int:pk>/informe/', views.api_informe_social, name='api_informe_social'),
    path('api/solicitudes/', views.api_solicitudes_sociales, name='api_solicitudes_sociales'),
    path('api/solicitudes/<int:pk>/resolver/', views.api_resolver_solicitud_social, name='api_resolver_solicitud_social'),
    path('api/notificaciones/', views.api_notificaciones_sociales, name='api_notificaciones_sociales'),
]
