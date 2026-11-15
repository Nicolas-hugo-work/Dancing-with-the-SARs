"""Importación de los incidentes registrados por el GAMC (servicio Emergencias)."""

import re
import unicodedata
from datetime import date, datetime

from django.contrib.gis.geos import Point

from incidentes.models import ClaseIncidente, Incidente
from territorio.errores import ImportacionError
from territorio.espacial import cuenca_que_contiene, distrito_que_contiene
from territorio.importacion import Capa, Origen, Resumen

# Fecha ISO, con hora y zona opcionales detrás: "2024-02-10", "2024-02-10T23:30:00-04:00", "…Z".
FECHA_ISO = re.compile(
    r"(\d{4}-\d{2}-\d{2})(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?"
)
# Primero la más específica: un «desborde por riada» es una riada.
PALABRAS_POR_CLASE = (
    (ClaseIncidente.RIADA_MAZAMORRA, ("riada", "mazamorra")),
    (ClaseIncidente.INUNDACION, ("inundac",)),
)


def clase_desde_tipo(tipo: str) -> str:
    """Clase del incidente a partir del tipo de evento de la fuente, sin tildes ni mayúsculas."""
    normalizado = sin_tildes(tipo).casefold()
    for clase, palabras in PALABRAS_POR_CLASE:
        if any(palabra in normalizado for palabra in palabras):
            return clase
    return ClaseIncidente.OTRO


def sin_tildes(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(caracter for caracter in descompuesto if not unicodedata.combining(caracter))


def fecha_desde_origen(valor: object) -> date:
    """La fecha tal como la escribió la fuente, sin convertir su zona horaria (pendiente GAMC)."""
    try:
        return interpretar_fecha(valor)
    except ValueError:
        raise ImportacionError(f"no es una fecha AAAA-MM-DD: {valor!r}") from None


def interpretar_fecha(valor: object) -> date:
    """Lanza ValueError si `valor` no es una fecha, o no existe (p. ej. 2024-13-40)."""
    match valor:
        case datetime():
            return valor.date()
        case date():
            return valor
        case str() if encontrada := FECHA_ISO.fullmatch(valor.strip()):
            return date.fromisoformat(encontrada[1])
    raise ValueError(valor)


def completar_incidente(registro: dict) -> dict:
    ubicacion = registro["geom"]
    return {
        **registro,
        "clase": clase_desde_tipo(registro["tipo_evento_origen"]),
        "distrito": distrito_que_contiene(ubicacion),
        "cuenca": cuenca_que_contiene(ubicacion),
    }


# Propiedades de origen provisionales hasta la sonda del WMS del GAMC (paso 10);
# `--campo` las cambia.
CAPA_INCIDENTES = Capa(
    nombre="incidentes",
    modelo=Incidente,
    claves=("id_origen",),
    campos={
        "id_origen": Origen("ID"),
        "fecha": Origen("FECHA", fecha_desde_origen),
        "tipo_evento_origen": Origen("TIPO"),
    },
    tipo_geom=Point,
    completar=completar_incidente,
)


def incidentes_sin_distrito(resumen: Resumen) -> list[str]:
    """Los incidentes de esta importación que no caen en ningún distrito cargado."""
    return list(
        Incidente.objects.filter(cargado_en=resumen.cargado_en, distrito__isnull=True)
        .order_by("id_origen")
        .values_list("id_origen", flat=True)
    )
