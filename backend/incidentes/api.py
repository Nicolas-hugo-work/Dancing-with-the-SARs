from incidentes.models import Incidente
from territorio.api import CapaPublicaSerializer, CapaPublicaViewSet


class IncidenteSerializer(CapaPublicaSerializer):
    class Meta(CapaPublicaSerializer.Meta):
        model = Incidente
        fields = ("id", "id_origen", "fecha", "clase", "distrito", "cuenca", "geom")


class IncidenteViewSet(CapaPublicaViewSet):
    queryset = Incidente.objects.order_by("fecha", "id_origen")
    serializer_class = IncidenteSerializer
    filterset_fields = ("clase",)
