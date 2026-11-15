from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from incidentes.models import Incidente
from territorio.admin import PROCEDENCIA_DE_SOLO_LECTURA


@admin.register(Incidente)
class IncidenteAdmin(GISModelAdmin):
    list_display = ("id_origen", "fecha", "clase", "distrito", "personas_afectadas", "conjunto")
    list_filter = ("clase", "conjunto")
    search_fields = ("id_origen", "tipo_evento_origen")
    date_hierarchy = "fecha"
    list_select_related = ("distrito",)
    readonly_fields = PROCEDENCIA_DE_SOLO_LECTURA
