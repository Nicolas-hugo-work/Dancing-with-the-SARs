"""Opciones de línea de comandos comunes a los comandos de importación por archivo."""

from argparse import ArgumentParser
from pathlib import Path

from django.core.management import CommandError

from territorio.errores import ImportacionError
from territorio.importacion import Capa, Importacion, Resumen, leer_archivo, parsear_mapeo

AYUDA_SRID = (
    "EPSG de las geometrías sin sistema declarado o en el WGS 84 implícito de GeoJSON; "
    "debe coincidir con cualquier otro sistema declarado"
)


def agregar_opciones(parser: ArgumentParser):
    fuente = parser.add_mutually_exclusive_group(required=True)
    fuente.add_argument("--archivo", type=Path, help="GeoJSON, Shapefile u otra fuente de GDAL")
    parser.add_argument("--srid", type=int, help=AYUDA_SRID)
    parser.add_argument(
        "--campo",
        action="append",
        default=[],
        metavar="CAMPO=PROPIEDAD",
        help="propiedad de origen de un campo; puede repetirse",
    )
    parser.add_argument(
        "--esperados", type=int, help="número de entidades que debe traer la fuente"
    )


def importar_con_opciones(capa: Capa, opciones: dict) -> Resumen:
    archivo = Path(opciones["archivo"])
    try:
        importacion = Importacion(
            parsear_mapeo(opciones["campo"], capa),
            fuente=f"archivo:{archivo.name}",
            srid_indicado=opciones["srid"],
            esperados=opciones["esperados"],
        )
        return importacion.importar(leer_archivo(archivo))
    except ImportacionError as error:
        raise CommandError(str(error)) from None


def describir_resumen(capa: Capa, resumen: Resumen) -> str:
    return (
        f"{capa.nombre}: {resumen.creados} creados, {resumen.actualizados} actualizados, "
        f"{resumen.reparadas} geometrías reparadas"
    )
