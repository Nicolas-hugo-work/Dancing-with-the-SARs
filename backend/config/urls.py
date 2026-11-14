from django.urls import path

from config.salud import healthz

urlpatterns = [
    path("healthz/", healthz, name="healthz"),
]
