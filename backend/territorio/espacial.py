"""Consultas espaciales con las que los importadores asignan distrito y cuenca a sus registros.

La regla entre cuencas anidadas (uh7, uh8 e influencia se solapan) es provisional y está pendiente
de confirmar con datos reales (README). A un punto le corresponde la cuenca de menor área que lo
cubre; a un cauce, la que contiene más longitud de él, y a igual longitud, la de menor área. Los
desempates finales son la capa y el código. Áreas y longitudes se miden en UTM 19 S.
"""

from django.contrib.gis.db.models.functions import Area, Intersection, Length, Transform
from django.contrib.gis.geos import MultiLineString, Point
from django.db.models.functions import Round

from territorio.models import Cuenca, Distrito

# Áreas y longitudes en UTM 19 S, como fija el proyecto; en EPSG:4326 el área saldría en grados².
SRID_METRICO = 32719
# Longitudes redondeadas al centímetro: el ruido de coma flotante no debe decidir un desempate.
DECIMALES_DE_LONGITUD = 2


def distrito_que_contiene(punto: Point) -> Distrito | None:
    """El distrito que cubre el punto; en un borde común, el de menor código."""
    return Distrito.objects.filter(geom__covers=punto).order_by("codigo").first()


def cuenca_que_contiene(punto: Point) -> Cuenca | None:
    return (
        Cuenca.objects.filter(geom__covers=punto)
        .annotate(area=area_metrica())
        .order_by("area", "capa_origen", "codigo")
        .first()
    )


def cuenca_de_mayor_interseccion(linea: MultiLineString) -> Cuenca | None:
    """La cuenca que contiene más longitud de la línea; None si solo toca bordes."""
    candidata = (
        Cuenca.objects.filter(geom__intersects=linea)
        .annotate(
            longitud=Round(
                Length(Transform(Intersection("geom", linea), SRID_METRICO)), DECIMALES_DE_LONGITUD
            ),
            area=area_metrica(),
        )
        .order_by("-longitud", "area", "capa_origen", "codigo")
        .first()
    )
    if candidata is None or candidata.longitud.m <= 0:
        return None
    return candidata


def area_metrica() -> Area:
    return Area(Transform("geom", SRID_METRICO))
