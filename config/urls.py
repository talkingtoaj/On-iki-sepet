"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from config.health import health_check

urlpatterns = [
    path('admin/', admin.site.urls),
    # Unauthenticated on purpose: the platform's health checker cannot
    # sign in, and the response exposes nothing beyond reachability.
    path('health/', health_check, name='health_check'),
    path("auth/", include("django.contrib.auth.urls")),
    # Provides set_language, which the language selector posts to.
    path("i18n/", include("django.conf.urls.i18n")),
    path("", include("onikisepet.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Renders a "waiting for access" page for accounts with no role yet.
handler403 = "onikisepet.views.permission_denied"
