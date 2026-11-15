"""Importación de capas externas (archivo GeoJSON o Shapefile) a los modelos de territorio.

Lo que cambia de una capa a otra se declara en su `Capa`: de qué propiedad sale cada campo y cómo
se convierte (`Origen`), los valores fijos y los campos derivados (`completar`). El recorrido
leer -> normalizar -> mapear -> completar -> validar -> escribir es el mismo para todas.
"""

import math
import os
import re
from collections import Counter
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from datetime import date, datetime, time
from pathlib import Path
from typing import NamedTuple

from django.contrib.gis.db.models import GeometryField
from django.contrib.gis.gdal import DataSource, GDALException, OGRGeometry
from django.contrib.gis.gdal.feature import Feature
from django.contrib.gis.gdal.layer import Layer
from django.contrib.gis.geos import GEOSGeometry, MultiLineString, MultiPolygon
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import CheckConstraint, ForeignKey, Model
from django.utils import timezone

from territorio.errores import ImportacionError
from territorio.espacial import cuenca_de_mayor_interseccion
from territorio.geometria import Normalizacion, horizontal
from territorio.models import (
    NIVEL_POR_CAPA,
    CapaCuenca,
    Cuenca,
    Distrito,
    TipoDrenaje,
    Torrentera,
)

OPCION_FECHAS_COMO_TEXTO = "OGR_GEOJSON_DATE_AS_STRING"
# RFC 7946: todo GeoJSON está en WGS 84 y el miembro «crs» ya no existe.
SRID_GEOJSON = 4326
FORMATO_GEOJSON = "GeoJSON"  # nombre del driver de GDAL
# Un número entero con un prefijo opcional sin dígitos: "7", "D7", "Distrito 7", " 12 ".
ENTERO_CON_PREFIJO = re.compile(r"\s*[^\d\s-]*\s*(\d+)\s*")

# Todo conversor lanza ImportacionError, con el valor recibido, si no puede convertirlo.
Conversor = Callable[[object], object]
Completar = Callable[[dict], dict]


def texto(valor: object) -> str:
    """Texto de una propiedad de origen; los reales enteros que entrega OGR pierden el «.0»."""
    match valor:
        case None:
            return ""
        case float() if not math.isfinite(valor):
            raise ImportacionError(f"no es un valor de texto válido: {valor!r}")
        case float() if valor.is_integer():
            return str(int(valor))
        case float():
            return repr(valor)
    return str(valor).strip()


def entero(valor: object) -> int:
    try:
        return interpretar_entero(valor)
    except ValueError:
        raise ImportacionError(f"no es un número entero: {valor!r}") from None


def interpretar_entero(valor: object) -> int:
    """Lanza ValueError si `valor` no es un entero; int() también, si pasa de 4300 dígitos."""
    match valor:
        case bool():
            pass
        case int():
            return valor
        case float() if valor.is_integer():
            return int(valor)
        case str() if encontrado := ENTERO_CON_PREFIJO.fullmatch(valor):
            return int(encontrado[1])
    raise ValueError(valor)


def valor_json(valor: object) -> object:
    """Valor apto para `atributos_origen`: OGR tipa fechas y horas, y JSON no las admite."""
    match valor:
        case date() | time():
            return valor.isoformat()
        case float() if not math.isfinite(valor):
            return repr(valor)
    return valor


class Origen(NamedTuple):
    """De qué propiedad de la fuente sale un campo y cómo se convierte."""

    propiedad: str
    conversor: Conversor = texto


@dataclass(frozen=True)
class Entidad:
    """Una entidad de la fuente; `geom` es None si la fuente no trae geometría."""

    propiedades: Mapping[str, object]
    geom: OGRGeometry | None
    # El SRS de `geom` es el WGS 84 implícito de GeoJSON (RFC 7946), lo repita o no un «crs»:
    # GDAL no los distingue, así que no prueba que la fuente lo haya declarado.
    srs_implicito: bool = False


def sin_completar(registro: dict) -> dict:
    return registro


@dataclass(frozen=True)
class Capa:
    """Cómo se importa una capa externa a su modelo."""

    nombre: str
    modelo: type[Model]
    # Campos que identifican el registro al reimportar; coinciden con una restricción única.
    claves: tuple[str, ...]
    campos: Mapping[str, Origen]
    tipo_geom: type[GEOSGeometry]
    fijos: Mapping[str, object] = field(default_factory=dict)
    # Campos derivados de los ya mapeados, como la cuenca de una torrentera.
    completar: Completar = sin_completar


def parsear_mapeo(asignaciones: Sequence[str], capa: Capa) -> Capa:
    """Devuelve la capa con las propiedades de origen cambiadas por `--campo campo=PROPIEDAD`."""
    campos = dict(capa.campos)
    for asignacion in asignaciones:
        campo, igual, propiedad = asignacion.partition("=")
        if not igual or not propiedad:
            raise ImportacionError(f"--campo {asignacion!r}: use la forma campo=PROPIEDAD")
        if campo not in campos:
            raise ImportacionError(
                f"--campo {campo!r} no es un campo de {capa.nombre}: {', '.join(sorted(campos))}"
            )
        campos[campo] = campos[campo]._replace(propiedad=propiedad)
    return replace(capa, campos=campos)


def mapear(entidad: Entidad, capa: Capa) -> dict:
    """Valores del modelo a partir de las propiedades, sin la geometría ni los campos derivados."""
    valores = {campo: valor_de(entidad, origen) for campo, origen in capa.campos.items()}
    atributos = {nombre: valor_json(valor) for nombre, valor in entidad.propiedades.items()}
    return {**valores, **capa.fijos, "atributos_origen": atributos}


def valor_de(entidad: Entidad, origen: Origen) -> object:
    if origen.propiedad not in entidad.propiedades:
        disponibles = ", ".join(sorted(entidad.propiedades))
        raise ImportacionError(f"falta la propiedad {origen.propiedad}; disponibles: {disponibles}")
    try:
        return origen.conversor(entidad.propiedades[origen.propiedad])
    except ImportacionError as error:
        raise ImportacionError(f"{origen.propiedad}: {error}") from None


def leer_archivo(ruta: Path) -> list[Entidad]:
    """Entidades de la única capa de un GeoJSON, un Shapefile u otra fuente que abra GDAL."""
    fuente = abrir(ruta)
    capa = unica_capa(fuente, ruta)
    return [entidad_de(rasgo, fuente.driver.name) for rasgo in capa]


def abrir(ruta: Path) -> DataSource:
    with fechas_como_texto():
        try:
            return DataSource(str(ruta))
        except GDALException:
            raise ImportacionError(f"no se pudo abrir {ruta} como fuente geográfica") from None


@contextmanager
def fechas_como_texto() -> Iterator[None]:
    """Conserva fechas y horas del GeoJSON tal como se escribieron, con su zona horaria.

    Sin esta opción GDAL las tipa y descarta la zona, que es un dato pendiente de confirmar.
    """
    anterior = os.environ.get(OPCION_FECHAS_COMO_TEXTO)
    os.environ[OPCION_FECHAS_COMO_TEXTO] = "YES"
    try:
        yield
    finally:
        if anterior is None:
            del os.environ[OPCION_FECHAS_COMO_TEXTO]
        else:
            os.environ[OPCION_FECHAS_COMO_TEXTO] = anterior


def unica_capa(fuente: DataSource, ruta: Path) -> Layer:
    if len(fuente) != 1:
        nombres = ", ".join(capa.name for capa in fuente)
        raise ImportacionError(
            f"{ruta} contiene {len(fuente)} capas ({nombres}): indique una fuente de una sola capa"
        )
    return fuente[0]


def entidad_de(rasgo: Feature, formato: str) -> Entidad:
    """`formato` es el driver de GDAL de la fuente; el SRS implícito se decide por geometría.

    Una geometría GeoJSON puede traer su propio «crs» (GeoJSON 2008) distinto del de la capa.
    """
    propiedades = {campo: rasgo.get(campo) for campo in rasgo.fields}
    geom = geometria_de(rasgo)
    return Entidad(propiedades, geom, formato == FORMATO_GEOJSON and en_wgs84(geom))


def en_wgs84(geom: OGRGeometry | None) -> bool:
    """Si la geometría está en WGS 84: 2D (EPSG:4326) o con altura (EPSG:4979)."""
    if geom is None or geom.srs is None:
        return False
    return horizontal(geom.srs.srid) == SRID_GEOJSON


def geometria_de(rasgo: Feature) -> OGRGeometry | None:
    try:
        return rasgo.geom
    except GDALException:
        # Forma nula: la informa la normalización junto con los demás errores de la capa.
        return None


@dataclass(frozen=True)
class Resumen:
    creados: int
    actualizados: int
    reparadas: int
    # El mismo instante para todos los registros escritos en esta importación.
    cargado_en: datetime


@dataclass(frozen=True)
class Importacion:
    """Importa las entidades de una fuente a su capa: todo o nada, sin borrar nunca."""

    capa: Capa
    # Procedencia que se guarda en `fuente_capa`, como "archivo:distritos.geojson".
    fuente: str
    srid_indicado: int | None = None
    esperados: int | None = None

    def importar(self, entidades: Sequence[Entidad]) -> Resumen:
        """Valida todas las entidades y, solo si ninguna falla, las escribe en una transacción.

        Lanza ImportacionError con todos los errores encontrados, cada uno con su posición.
        """
        preparadas = self._preparar(entidades)
        return self._escribir(preparadas)

    def _preparar(self, entidades: Sequence[Entidad]) -> list[tuple[dict, bool]]:
        normalizacion = Normalizacion(self.capa.tipo_geom, self.srid_indicado)
        preparadas, errores = [], []
        for posicion, entidad in enumerate(entidades, start=1):
            try:
                preparadas.append(self._registro(entidad, normalizacion))
            except ImportacionError as error:
                errores.append(f"entidad {posicion}: {error}")
        errores += self._claves_repetidas([registro for registro, _ in preparadas])
        errores += self._conteo_inesperado(len(entidades))
        if errores:
            raise ImportacionError("\n".join(errores))
        return preparadas

    def _registro(self, entidad: Entidad, normalizacion: Normalizacion) -> tuple[dict, bool]:
        geom, reparada = normalizacion.normalizar(entidad.geom, srs_implicito=entidad.srs_implicito)
        mapeado = {**mapear(entidad, self.capa), "geom": geom, "fuente_capa": self.fuente}
        registro = self.capa.completar(mapeado)
        validar_con_el_modelo(self.capa.modelo, registro)
        return registro, reparada

    def _claves_repetidas(self, registros: list[dict]) -> list[str]:
        conteo = Counter(self._clave(registro) for registro in registros)
        return [f"clave repetida {clave}" for clave, veces in conteo.items() if veces > 1]

    def _conteo_inesperado(self, total: int) -> list[str]:
        if self.esperados is None or self.esperados == total:
            return []
        return [f"se esperaban {self.esperados} entidades y la fuente tiene {total}"]

    def _escribir(self, preparadas: list[tuple[dict, bool]]) -> Resumen:
        ahora = timezone.now()
        creados = 0
        # Siempre en el orden de las claves: dos importaciones simultáneas bloquean igual.
        registros = sorted((registro for registro, _ in preparadas), key=self._clave)
        with transaction.atomic():
            for registro in registros:
                creados += self._guardar(registro, ahora)
        reparadas = sum(reparada for _, reparada in preparadas)
        return Resumen(creados, len(registros) - creados, reparadas, cargado_en=ahora)

    def _guardar(self, registro: dict, ahora: datetime) -> bool:
        claves = {campo: registro[campo] for campo in self.capa.claves}
        resto = {campo: valor for campo, valor in registro.items() if campo not in claves}
        _, creado = self.capa.modelo.objects.update_or_create(
            **claves, defaults={**resto, "cargado_en": ahora}
        )
        return creado

    def _clave(self, registro: dict) -> tuple:
        return tuple(registro[campo] for campo in self.capa.claves)


def validar_con_el_modelo(modelo: type[Model], registro: dict):
    """Longitudes, vacíos y restricciones CHECK del modelo, antes de escribir nada.

    No valida las únicas (rechazarían toda reimportación) ni las FK calculadas, que ya vienen
    de una consulta, ni la geometría, ya normalizada.
    """
    instancia = modelo(**registro)
    try:
        instancia.clean_fields(exclude=campos_sin_validar(modelo))
        validar_restricciones_check(instancia)
    except ValidationError as error:
        raise ImportacionError(describir(error)) from None


def validar_restricciones_check(instancia: Model):
    modelo = type(instancia)
    for restriccion in modelo._meta.constraints:
        if isinstance(restriccion, CheckConstraint):
            restriccion.validate(modelo, instancia)


def campos_sin_validar(modelo: type[Model]) -> list[str]:
    return [
        campo.name for campo in modelo._meta.fields if isinstance(campo, GeometryField | ForeignKey)
    ]


def describir(error: ValidationError) -> str:
    if hasattr(error, "error_dict"):
        return "; ".join(
            f"{campo}: {' '.join(mensajes)}" for campo, mensajes in error.message_dict.items()
        )
    return " ".join(error.messages)


def asignar_cuenca(registro: dict) -> dict:
    """Un cauce pertenece a la cuenca que contiene la mayor parte de su longitud."""
    return {**registro, "cuenca": cuenca_de_mayor_interseccion(registro["geom"])}


# Propiedades de origen provisionales hasta la sonda del WMS del GAMC (paso 10);
# `--campo` las cambia.
CAMPOS_DE_CUENCA = {"codigo": Origen("CODIGO"), "nombre": Origen("NOMBRE")}
CAMPOS_DE_DRENAJE = {"id_origen": Origen("ID"), "nombre": Origen("NOMBRE")}
CAPA_DE_DRENAJE_POR_TIPO = {
    TipoDrenaje.TORRENTERA: "torrenteras",
    TipoDrenaje.CANAL: "canales",
    TipoDrenaje.RIO: "rios",
}

CAPAS = {
    capa.nombre: capa
    for capa in (
        Capa(
            nombre="distritos",
            modelo=Distrito,
            claves=("codigo",),
            campos={"codigo": Origen("DISTRITO", entero), "nombre": Origen("NOMBRE")},
            tipo_geom=MultiPolygon,
        ),
        *(
            Capa(
                nombre=f"cuencas_{capa_origen}",
                modelo=Cuenca,
                claves=("capa_origen", "codigo"),
                campos=CAMPOS_DE_CUENCA,
                tipo_geom=MultiPolygon,
                fijos={"capa_origen": capa_origen, "nivel": NIVEL_POR_CAPA.get(capa_origen)},
            )
            for capa_origen in CapaCuenca
        ),
        *(
            Capa(
                nombre=nombre,
                modelo=Torrentera,
                claves=("tipo", "id_origen"),
                campos=CAMPOS_DE_DRENAJE,
                tipo_geom=MultiLineString,
                fijos={"tipo": tipo},
                completar=asignar_cuenca,
            )
            for tipo, nombre in CAPA_DE_DRENAJE_POR_TIPO.items()
        ),
    )
}
