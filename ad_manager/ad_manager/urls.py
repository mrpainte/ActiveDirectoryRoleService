"""Root URL configuration for AD Manager."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('directory/', include('directory.urls')),
    path('groups/', include('groups.urls')),
    path('dns/', include('dns_manager.urls')),
    path('gpo/', include('gpo.urls')),
    path('notifications/', include('notifications.urls')),
    path('audit/', include('audit.urls')),
    path('', include('directory.urls')),
]
