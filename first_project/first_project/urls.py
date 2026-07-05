"""
URL configuration for first_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponseForbidden

from django.conf import settings
from django.conf.urls.static import static


# Disable Django admin for non-technical users
def disabled_admin(request):
    return HttpResponseForbidden(
        "<h1>Access Denied</h1><p>This area is restricted. Please use the custom admin dashboard.</p>"
    )

urlpatterns = [
    path('', include('water_rental.urls')),  # Move this FIRST
    path('admin/', admin.site.urls),
    path('system-admin-panel/', admin.site.urls),
    path("__reload__/", include("django_browser_reload.urls")),
]



if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
