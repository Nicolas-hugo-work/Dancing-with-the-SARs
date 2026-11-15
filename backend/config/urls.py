from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import SimpleRouter

from config.salud import healthz
from incidentes.api import IncidenteViewSet
from territorio.api import CuencaViewSet, DistritoViewSet, TorrenteraViewSet

capas_publicas = SimpleRouter()
capas_publicas.register("distritos", DistritoViewSet)
capas_publicas.register("cuencas", CuencaViewSet)
capas_publicas.register("torrenteras", TorrenteraViewSet)
capas_publicas.register("incidentes", IncidenteViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz/", healthz, name="healthz"),
    path("api/v1/", include(capas_publicas.urls)),
    path("api/schema/", SpectacularAPIView.as_view(), name="esquema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="esquema"), name="swagger"),
]
