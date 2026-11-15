from django.contrib import admin

from riesgo.models import Alerta, IndiceRiesgo
from territorio.restricciones import UNIDADES


@admin.register(IndiceRiesgo)
class IndiceRiesgoAdmin(admin.ModelAdmin):
    list_display = (
        "fecha_hora_ref",
        "tipo",
        "distrito",
        "cuenca",
        "valor",
        "nivel",
        "version_metodo",
    )
    list_filter = ("tipo", "nivel", "version_metodo")
    date_hierarchy = "fecha_hora_ref"
    list_select_related = UNIDADES
    # Un JSON vacío en el formulario llegaría como None a una columna NOT NULL.
    readonly_fields = ("componentes",)


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = (
        "vigente_desde",
        "vigente_hasta",
        "nivel",
        "amenaza",
        "distrito",
        "estado",
        "origen",
    )
    list_filter = ("estado", "nivel", "amenaza", "origen")
    date_hierarchy = "vigente_desde"
    # La serie de índices crece por unidad y hora: un <select> la cargaría entera.
    raw_id_fields = ("indice", "reemplaza")
