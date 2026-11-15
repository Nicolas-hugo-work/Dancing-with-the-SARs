from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from radar.models import EscenaSAR


@admin.register(EscenaSAR)
class EscenaSARAdmin(GISModelAdmin):
    list_display = (
        "id_producto",
        "polarizacion",
        "fecha_adquisicion",
        "paso_orbita",
        "orbita_relativa",
        "proveedor",
    )
    list_filter = ("polarizacion", "paso_orbita", "proveedor")
    search_fields = ("id_producto",)
    date_hierarchy = "fecha_adquisicion"
