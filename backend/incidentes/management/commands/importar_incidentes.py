from django.core.management.base import BaseCommand

from incidentes.importacion import CAPA_INCIDENTES, incidentes_sin_distrito
from territorio.management.opciones import (
    agregar_opciones,
    describir_resumen,
    importar_con_opciones,
)


class Command(BaseCommand):
    help = (
        "Importa incidentes desde un archivo y les asigna distrito y cuenca por ubicación; "
        "importe antes el territorio. Informa los incidentes que quedan sin distrito."
    )

    def add_arguments(self, parser):
        agregar_opciones(parser)

    def handle(self, *args, **opciones):
        resumen = importar_con_opciones(CAPA_INCIDENTES, opciones)
        self.stdout.write(describir_resumen(CAPA_INCIDENTES, resumen))
        if sin_distrito := incidentes_sin_distrito(resumen):
            self.stdout.write(
                f"sin distrito (fuera de los distritos cargados): {', '.join(sin_distrito)}"
            )
