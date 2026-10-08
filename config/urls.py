from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('activities/', include('activities.urls')),
    path('organization/', include(('organization.urls', 'organization_direct'), namespace='organization_direct')),
    path('api/', include('activities.urls')),
    path('api/', include('organization.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / 'static')