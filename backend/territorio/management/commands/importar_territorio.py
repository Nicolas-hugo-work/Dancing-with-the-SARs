from django.core.management.base import BaseCommand

from territorio.importacion import CAPAS
from territorio.management.opciones import (
    agregar_opciones,
    describir_resumen,
    importar_con_opciones,
)


class Command(BaseCommand):
    help = (
        "Importa una capa de territorio desde un archivo, sin borrar nada: crea o actualiza "
        "cada registro por su clave y aborta sin escribir si alguna entidad tiene errores."
    )

    def add_arguments(self, parser):
        parser.add_argument("capa", choices=sorted(CAPAS))
        agregar_opciones(parser)

    def handle(self, *args, **opciones):
        capa = CAPAS[opciones["capa"]]
        resumen = importar_con_opciones(capa, opciones)
        self.stdout.write(describir_resumen(capa, resumen))
