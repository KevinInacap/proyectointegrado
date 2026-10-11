from django.urls import path
from .views import catalog_collection, catalog_detail

urlpatterns = [
    path('<str:catalog>/', catalog_collection, name='catalog_collection'),
    path('<str:catalog>/<int:pk>/', catalog_detail, name='catalog_detail'),
]
