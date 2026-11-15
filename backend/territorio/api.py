from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from territorio.models import Cuenca, Distrito, Torrentera

# Seis decimales de grado son unos 10 cm: suficiente para un mapa y sin coordenadas infladas.
GEOMETRIA_CON_6_DECIMALES = {"geom": {"precision": 6}}


class CapaPublicaSerializer(GeoFeatureModelSerializer):
    """Feature GeoJSON de una capa pública; cada subclase declara su modelo y sus campos."""

    class Meta:
        geo_field = "geom"
        extra_kwargs = GEOMETRIA_CON_6_DECIMALES


class CapaPublicaViewSet(ReadOnlyModelViewSet):
    """Lectura pública y sin paginar: el visor carga cada capa completa como FeatureCollection."""

    authentication_classes = ()
    permission_classes = (AllowAny,)
    pagination_class = None

    def get_queryset(self):
        # Solo las columnas publicadas: los atributos de origen y las zonas de influencia pesan.
        return super().get_queryset().only(*self.serializer_class.Meta.fields)


class DistritoSerializer(CapaPublicaSerializer):
    class Meta(CapaPublicaSerializer.Meta):
        model = Distrito
        fields = ("id", "codigo", "nombre", "subalcaldia", "tipo_area", "geom")


class CuencaSerializer(CapaPublicaSerializer):
    class Meta(CapaPublicaSerializer.Meta):
        model = Cuenca
        fields = ("id", "capa_origen", "codigo", "nivel", "nombre", "geom")


class TorrenteraSerializer(CapaPublicaSerializer):
    class Meta(CapaPublicaSerializer.Meta):
        model = Torrentera
        fields = ("id", "tipo", "id_origen", "nombre", "cuenca", "geom")


class DistritoViewSet(CapaPublicaViewSet):
    queryset = Distrito.objects.order_by("codigo")
    serializer_class = DistritoSerializer


class CuencaViewSet(CapaPublicaViewSet):
    queryset = Cuenca.objects.order_by("capa_origen", "codigo")
    serializer_class = CuencaSerializer
    filterset_fields = ("capa_origen",)


class TorrenteraViewSet(CapaPublicaViewSet):
    queryset = Torrentera.objects.order_by("tipo", "id_origen")
    serializer_class = TorrenteraSerializer
    filterset_fields = ("tipo",)
