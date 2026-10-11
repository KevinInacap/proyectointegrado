from django.urls import path
from .views import catalog_collection, catalog_detail, periods_reference

urlpatterns = [
    path('periods/', periods_reference, name='periods_reference'),
    path('<str:catalog>/', catalog_collection, name='catalog_collection'),
    path('<str:catalog>/<int:pk>/', catalog_detail, name='catalog_detail'),
]
