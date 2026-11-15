import operator
from functools import reduce

from django.db import models

from territorio.models import UnidadTerritorialAbstracta
from territorio.restricciones import entre, posterior, unica_por_unidad, valor_en


class MedicionPeriodicaAbstracta(UnidadTerritorialAbstracta):
    """Valor satelital agregado sobre una unidad territorial durante un período [inicio, fin)."""

    inicio = models.DateTimeField()
    fin = models.DateTimeField()
    version_producto = models.CharField(max_length=30)
    ingerido_en = models.DateTimeField(auto_now_add=True)

    class Meta(UnidadTerritorialAbstracta.Meta):
        abstract = True
        constraints = (*UnidadTerritorialAbstracta.Meta.constraints, posterior("fin", "inicio"))


class FuenteLluvia(models.TextChoices):
    IMERG_EARLY = "imerg_early", "IMERG Early"
    IMERG_LATE = "imerg_late", "IMERG Late"
    IMERG_FINAL = "imerg_final", "IMERG Final"
    CHIRPS3_PRELIM = "chirps3_prelim", "CHIRPS v3 preliminar"
    CHIRPS3_FINAL = "chirps3_final", "CHIRPS v3 final"


class MetodoAgregacion(models.TextChoices):
    MEDIA_AREA = "media_area", "Media ponderada por área"
    MAXIMO = "maximo", "Máximo"


# Cota de cordura: supera con holgura el récord mundial de lluvia en 24 h (1825 mm).
LLUVIA_MAXIMA_MM = 10000


class LecturaLluvia(MedicionPeriodicaAbstracta):
    valor_mm = models.FloatField()
    fuente = models.CharField(max_length=20, choices=FuenteLluvia)
    metodo_agregacion = models.CharField(max_length=20, choices=MetodoAgregacion)
    fraccion_valida = models.FloatField()

    class Meta(MedicionPeriodicaAbstracta.Meta):
        constraints = (
            *MedicionPeriodicaAbstracta.Meta.constraints,
            *unica_por_unidad("fuente", "metodo_agregacion", "inicio", "fin", "version_producto"),
            entre("valor_mm", (0, LLUVIA_MAXIMA_MM)),
            entre("fraccion_valida", (0, 1)),
            valor_en("fuente", FuenteLluvia.values),
            valor_en("metodo_agregacion", MetodoAgregacion.values),
        )

    def __str__(self):
        return f"{self.fuente} {self.inicio:%Y-%m-%d %H:%M} {self.valor_mm} mm"


class UnidadHumedad(models.TextChoices):
    M3_M3 = "m3_m3", "m³/m³"
    PCT_SATURACION = "pct_saturacion", "% de saturación"


class CapaSuelo(models.TextChoices):
    SUPERFICIAL = "superficial", "Superficial"
    ZONA_RAIZ = "zona_raiz", "Zona radicular"


class FuenteHumedad(models.TextChoices):
    SMAP_9KM = "smap_9km", "SMAP 9 km"
    CLMS_SWI = "clms_swi", "CLMS SWI"


RANGO_POR_UNIDAD = {UnidadHumedad.M3_M3: (0, 1), UnidadHumedad.PCT_SATURACION: (0, 100)}


def valor_en_rango_de_su_unidad() -> models.CheckConstraint:
    """Cada unidad tiene su rango; de paso limita unidad_medida a las del catálogo."""
    rangos = (
        models.Q(unidad_medida=unidad, valor__range=rango)
        for unidad, rango in RANGO_POR_UNIDAD.items()
    )
    mensaje = " o ".join(
        f"de {minimo} a {maximo} {unidad.label}"
        for unidad, (minimo, maximo) in RANGO_POR_UNIDAD.items()
    )
    return models.CheckConstraint(
        condition=reduce(operator.or_, rangos),
        name="%(app_label)s_%(class)s_valor_en_rango_de_su_unidad",
        violation_error_message=f"Valor {mensaje}.",
    )


class HumedadSuelo(MedicionPeriodicaAbstracta):
    valor = models.FloatField()
    unidad_medida = models.CharField(max_length=20, choices=UnidadHumedad)
    capa = models.CharField(max_length=20, choices=CapaSuelo)
    fuente = models.CharField(max_length=20, choices=FuenteHumedad)

    class Meta(MedicionPeriodicaAbstracta.Meta):
        constraints = (
            *MedicionPeriodicaAbstracta.Meta.constraints,
            *unica_por_unidad("fuente", "capa", "inicio", "fin", "version_producto"),
            valor_en_rango_de_su_unidad(),
            valor_en("capa", CapaSuelo.values),
            valor_en("fuente", FuenteHumedad.values),
        )

    def __str__(self):
        return f"{self.fuente} {self.capa} {self.inicio:%Y-%m-%d} {self.valor} {self.unidad_medida}"
