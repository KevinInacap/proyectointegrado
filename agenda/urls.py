from django.urls import path

from . import views

app_name = "agenda"

urlpatterns = [
    path("", views.api_agenda, name="api_agenda"),
]
