from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from territorio.models import Cuenca, Distrito, Torrentera

# Un JSON vacío en el formulario llegaría como None a una columna NOT NULL.
PROCEDENCIA_DE_SOLO_LECTURA = ("atributos_origen",)


@admin.register(Distrito)
class DistritoAdmin(GISModelAdmin):
    list_display = ("codigo", "nombre", "subalcaldia", "tipo_area", "poblacion")
    list_filter = ("subalcaldia", "tipo_area")
    search_fields = ("nombre",)
    ordering = ("codigo",)
    readonly_fields = PROCEDENCIA_DE_SOLO_LECTURA


@admin.register(Cuenca)
class CuencaAdmin(GISModelAdmin):
    list_display = ("codigo", "nombre", "capa_origen", "nivel")
    list_filter = ("capa_origen", "nivel")
    search_fields = ("codigo", "nombre")
    readonly_fields = PROCEDENCIA_DE_SOLO_LECTURA


@admin.register(Torrentera)
class TorrenteraAdmin(GISModelAdmin):
    list_display = ("id_origen", "nombre", "tipo", "cuenca")
    list_filter = ("tipo",)
    search_fields = ("id_origen", "nombre")
    # select_related() sin argumentos no sigue FK anulables: sin esto, una consulta por fila.
    list_select_related = ("cuenca",)
    readonly_fields = PROCEDENCIA_DE_SOLO_LECTURA
