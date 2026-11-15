from django.contrib import admin

from clima.models import HumedadSuelo, LecturaLluvia
from territorio.restricciones import UNIDADES

# list_select_related = UNIDADES en los admin de series: select_related() sin argumentos no
# sigue FK anulables, y las dos de la unidad territorial lo son por el XOR.


@admin.register(LecturaLluvia)
class LecturaLluviaAdmin(admin.ModelAdmin):
    list_display = ("inicio", "fin", "distrito", "cuenca", "fuente", "valor_mm", "fraccion_valida")
    list_filter = ("fuente", "metodo_agregacion")
    date_hierarchy = "inicio"
    list_select_related = UNIDADES


@admin.register(HumedadSuelo)
class HumedadSueloAdmin(admin.ModelAdmin):
    list_display = (
        "inicio",
        "fin",
        "distrito",
        "cuenca",
        "fuente",
        "capa",
        "valor",
        "unidad_medida",
    )
    list_filter = ("fuente", "capa")
    date_hierarchy = "inicio"
    list_select_related = UNIDADES
