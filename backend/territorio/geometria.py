"""Normalización de las geometrías importadas al tipo y al sistema de referencia de cada capa."""

import math
from collections.abc import Iterator
from dataclasses import dataclass
from typing import NamedTuple

from django.contrib.gis.gdal import GDALException, OGRGeometry, SpatialReference
from django.contrib.gis.geos import (
    GeometryCollection,
    GEOSException,
    GEOSGeometry,
    LineString,
    MultiLineString,
    MultiPolygon,
    Point,
    Polygon,
)

from territorio.errores import ImportacionError

SRID_CAPAS = 4326
# Tipo simple que cada tipo múltiple admite como una sola parte.
PARTE_DE = {MultiPolygon: Polygon, MultiLineString: LineString}
# Dimensión topológica de cada tipo de capa (GEOS: 0 punto, 1 línea, 2 superficie).
DIMENSION_SUPERFICIE = 2
DIMENSION = {Point: 0, MultiLineString: 1, MultiPolygon: DIMENSION_SUPERFICIE}
# Caja aproximada del municipio de Cochabamba, incluido el Parque Tunari, y un margen que admite
# los incidentes y las cuencas limítrofes; un punto con lat y lon intercambiadas queda fuera.
EXTENSION_MUNICIPIO = (-66.30, -17.50, -66.05, -17.25)
MARGEN_EXTENSION_GRADOS = 0.5
EXTENSION_ADMITIDA = Polygon.from_bbox(
    (
        EXTENSION_MUNICIPIO[0] - MARGEN_EXTENSION_GRADOS,
        EXTENSION_MUNICIPIO[1] - MARGEN_EXTENSION_GRADOS,
        EXTENSION_MUNICIPIO[2] + MARGEN_EXTENSION_GRADOS,
        EXTENSION_MUNICIPIO[3] + MARGEN_EXTENSION_GRADOS,
    )
)
EXTENSION_ADMITIDA.srid = SRID_CAPAS
# Un GeoJSON con altura declara WGS 84 3D (EPSG:4979): misma horizontal que EPSG:4326.
SISTEMA_HORIZONTAL = {4979: 4326}


def horizontal(srid: int) -> int:
    return SISTEMA_HORIZONTAL.get(srid, srid)


def en_2d_y_4326(geom: OGRGeometry) -> OGRGeometry:
    """Pasa a líneas rectas, a 2D y a EPSG:4326 una geometría con su SRS ya asignado."""
    if not geom.geos_support:
        # Curvas (CurvePolygon, MultiSurface, MultiCurve): GEOS solo admite tramos rectos.
        geom = geom.get_linear_geometry()
    # Las columnas son 2D: PostGIS rechazaría una altura Z al escribir.
    geom.set_3d(False)
    transformar_a_4326(geom)
    return geom


def transformar_a_4326(geom: OGRGeometry):
    srs = geom.srs
    origen = f"EPSG:{srs.srid}" if srs.srid else f"el sistema declarado ({srs.name})"
    try:
        geom.transform(SRID_CAPAS)
    except GDALException:
        raise ImportacionError(
            f"no se pudo transformar desde {origen} a EPSG:{SRID_CAPAS}: "
            "coordenadas fuera del dominio de la proyección"
        ) from None


def geos_de(geom: OGRGeometry) -> GEOSGeometry:
    """La geometría en GEOS; rechaza las que GEOS no admite, las vacías y las no finitas."""
    try:
        geos = geom.geos
    except GEOSException:
        raise ImportacionError(f"geometría {geom.geom_name} no admitida por GEOS") from None
    # POINT(nan nan) no está vacío para OGR, pero GEOS lo lee como POINT EMPTY.
    if geos.empty:
        raise ImportacionError("entidad sin geometría (nula o vacía)")
    if not all(math.isfinite(numero) for numero in numeros(geos.coords)):
        raise ImportacionError("coordenadas no finitas (NaN o infinito)")
    return geos


def numeros(coordenadas: object) -> Iterator[float]:
    """Todos los números de las coordenadas anidadas de una geometría."""
    if isinstance(coordenadas, tuple | list):
        for valor in coordenadas:
            yield from numeros(valor)
    else:
        yield coordenadas


def comprobar_extension(geom: GEOSGeometry):
    if not EXTENSION_ADMITIDA.covers(geom):
        raise ImportacionError(
            f"geometría fuera de la extensión del municipio {geom.extent}: "
            "¿ejes invertidos o sistema de referencia equivocado?"
        )


def es_coleccion_de_una_parte(geom: GEOSGeometry) -> bool:
    return isinstance(geom, GeometryCollection) and len(geom) == 1


def partes_simples(geom: GEOSGeometry) -> Iterator[GEOSGeometry]:
    """Recorre las partes no compuestas, también dentro de colecciones anidadas."""
    if isinstance(geom, GeometryCollection):
        for parte in geom:
            yield from partes_simples(parte)
    else:
        yield geom


class GeometriaNormalizada(NamedTuple):
    geom: GEOSGeometry
    reparada: bool


@dataclass(frozen=True)
class Normalizacion:
    """Cómo llevar las geometrías de una capa a su tipo en EPSG:4326."""

    tipo: type[GEOSGeometry]
    # EPSG de las geometrías sin sistema declarado; también prevalece sobre el WGS 84 implícito de
    # GeoJSON (RFC 7946), lo repita o no un «crs» heredado. Otro sistema declarado debe coincidir.
    srid_indicado: int | None = None

    def __post_init__(self):
        if self.srid_indicado is not None:
            try:
                SpatialReference(self.srid_indicado)
            except GDALException:
                raise ImportacionError(
                    f"--srid {self.srid_indicado} no es un código EPSG conocido"
                ) from None

    def normalizar(
        self, geom: OGRGeometry | None, *, srs_implicito: bool = False
    ) -> GeometriaNormalizada:
        """Devuelve la geometría en 2D, en EPSG:4326 y del tipo de la capa; no modifica `geom`.

        `geom` es None cuando la entidad de origen no trae geometría (shapefiles con formas nulas).
        `srs_implicito` indica que el SRS es el WGS 84 implícito del formato (RFC 7946), que GDAL
        asigna haya o no un «crs» heredado que lo repita; con --srid manda el indicado.
        """
        if geom is None or geom.empty:
            raise ImportacionError("entidad sin geometría (nula o vacía)")
        plana = geom.clone()
        self._asignar_srs(plana, srs_implicito=srs_implicito)
        geos = geos_de(en_2d_y_4326(plana))
        reparada = not geos.valid
        if reparada:
            geos = self._reparar(geos)
        normalizada = self._al_tipo_de_la_capa(geos)
        comprobar_extension(normalizada)
        return GeometriaNormalizada(normalizada, reparada)

    def _asignar_srs(self, geom: OGRGeometry, *, srs_implicito: bool):
        """Fija en `geom` el SRS que vale: el declarado, o --srid si falta o es el implícito."""
        if geom.srs is None or (srs_implicito and self.srid_indicado is not None):
            geom.srs = self._srid_para_geometria_sin_crs()
        elif self.srid_indicado is not None:
            self._comprobar_coherencia(geom.srs)

    def _reparar(self, geom: GEOSGeometry) -> GEOSGeometry:
        """Repara cada parte inválida y se queda con las partes de la dimensión de la capa.

        Las superficies se unen después: `make_valid` sobre el conjunto borraría el área donde dos
        partes válidas se solapan. Las capas de puntos no se reparan: un punto finito siempre es
        válido, así que lo inválido ahí es una colección que no corresponde a la capa.
        """
        if self.tipo not in PARTE_DE:
            raise ImportacionError(
                f"geometría inválida en una capa de {self.tipo.__name__}: {geom.valid_reason}"
            )
        reparadas = (parte if parte.valid else parte.make_valid() for parte in partes_simples(geom))
        dimension = DIMENSION[self.tipo]
        utiles = [p for r in reparadas for p in partes_simples(r) if p.dims == dimension]
        if not utiles:
            raise ImportacionError(f"la reparación no deja ninguna geometría {self.tipo.__name__}")
        reunidas = self.tipo(*utiles, srid=geom.srid)
        return reunidas.unary_union if dimension == DIMENSION_SUPERFICIE else reunidas

    def _srid_para_geometria_sin_crs(self) -> int:
        if self.srid_indicado is None:
            raise ImportacionError(
                "la geometría no declara su sistema de referencia: indique --srid"
            )
        return self.srid_indicado

    def _comprobar_coherencia(self, declarado: SpatialReference):
        if declarado.srid is None:
            raise ImportacionError(
                f"la geometría declara un sistema sin código EPSG ({declarado.name}): omita --srid"
            )
        if horizontal(declarado.srid) != horizontal(self.srid_indicado):
            raise ImportacionError(
                f"--srid {self.srid_indicado} contradice el sistema declarado EPSG:{declarado.srid}"
            )

    def _al_tipo_de_la_capa(self, geom: GEOSGeometry) -> GEOSGeometry:
        if isinstance(geom, self.tipo):
            return geom
        if isinstance(geom, PARTE_DE.get(self.tipo, ())):
            return self.tipo(geom, srid=geom.srid)
        if es_coleccion_de_una_parte(geom) and isinstance(geom[0], self.tipo):
            return geom[0]
        raise ImportacionError(
            f"tipo incompatible: {geom.geom_type} en una capa de {self.tipo.__name__}"
        )
