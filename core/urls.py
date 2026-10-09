from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.login_view, name='login'),
    path('recuperar-clave/', views.password_recovery_view, name='password_recovery'),
    path('logout/', views.logout_view, name='logout'),
]

