import operator
from functools import reduce

from django.contrib.gis.db import models
from django.db.models import CheckConstraint, Q, UniqueConstraint
from django.utils import timezone

from territorio.restricciones import exactamente_una_unidad, valor_en


class ImportadoAbstracto(models.Model):
    """Procedencia común de los registros cargados desde una capa externa (archivo o WMS)."""

    fuente_capa = models.CharField(max_length=100)
    atributos_origen = models.JSONField(default=dict, blank=True)
    # Momento de la última carga desde la fuente: lo renueva el importador, no una edición manual.
    cargado_en = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        abstract = True


class Subalcaldia(models.TextChoices):
    TUNARI = "tunari", "Tunari"
    MOLLE = "molle", "Molle"
    ALEJO_CALATAYUD = "alejo_calatayud", "Alejo Calatayud"
    VALLE_HERMOSO = "valle_hermoso", "Valle Hermoso"
    ADELA_ZAMUDIO = "adela_zamudio", "Adela Zamudio"
    ITOCTA = "itocta", "Itocta"
    KARA_KARA = "kara_kara", "K'ara K'ara"


class TipoArea(models.TextChoices):
    URBANO = "urbano", "Urbano"
    MIXTO = "mixto", "Mixto"
    RURAL = "rural", "Rural"
    AREA_PROTEGIDA = "area_protegida", "Área protegida"


class Distrito(ImportadoAbstracto):
    codigo = models.IntegerField()
    nombre = models.CharField(max_length=100)
    subalcaldia = models.CharField(max_length=20, choices=Subalcaldia, blank=True, default="")
    tipo_area = models.CharField(max_length=20, choices=TipoArea, blank=True, default="")
    poblacion = models.PositiveIntegerField(null=True, blank=True)
    geom = models.MultiPolygonField(srid=4326)

    class Meta:
        constraints = (
            UniqueConstraint(fields=["codigo"], name="territorio_distrito_codigo_unico"),
            CheckConstraint(condition=Q(codigo__gte=1), name="territorio_distrito_codigo_positivo"),
            valor_en("tipo_area", [*TipoArea.values, ""]),
        )

    def __str__(self):
        return f"D{self.codigo} {self.nombre}"


class CapaCuenca(models.TextChoices):
    UH7 = "uh7", "Unidades hidrográficas nivel 7"
    UH8 = "uh8", "Unidades hidrográficas nivel 8"
    INFLUENCIA = "influencia", "Cuencas de influencia"


# Nivel Pfafstetter de cada capa de unidades hidrográficas; las de influencia no tienen uno fijo.
NIVEL_POR_CAPA = {CapaCuenca.UH7: 7, CapaCuenca.UH8: 8}


def nivel_coherente_con_capa() -> Q:
    """Sin nivel, capa sin nivel fijo, o exactamente el nivel que corresponde a la capa."""
    niveles_de_capa = (Q(capa_origen=capa, nivel=nivel) for capa, nivel in NIVEL_POR_CAPA.items())
    sin_nivel_fijo = Q(nivel__isnull=True) | ~Q(capa_origen__in=list(NIVEL_POR_CAPA))
    return reduce(operator.or_, niveles_de_capa, sin_nivel_fijo)


class Cuenca(ImportadoAbstracto):
    codigo = models.CharField(max_length=30)
    nivel = models.PositiveSmallIntegerField(null=True, blank=True)
    capa_origen = models.CharField(max_length=20, choices=CapaCuenca)
    nombre = models.CharField(max_length=150, blank=True, default="")
    geom = models.MultiPolygonField(srid=4326)

    class Meta:
        constraints = (
            UniqueConstraint(
                fields=["capa_origen", "codigo"], name="territorio_cuenca_unica_por_capa"
            ),
            valor_en("capa_origen", CapaCuenca.values),
            valor_en("nivel", NIVEL_POR_CAPA.values()),
            CheckConstraint(
                condition=nivel_coherente_con_capa(),
                name="territorio_cuenca_nivel_coherente_con_capa",
            ),
        )

    def __str__(self):
        return f"{self.capa_origen} {self.codigo}"


class TipoDrenaje(models.TextChoices):
    TORRENTERA = "torrentera", "Torrentera"
    CANAL = "canal", "Canal"
    RIO = "rio", "Río"


class Torrentera(ImportadoAbstracto):
    id_origen = models.CharField(max_length=64)
    nombre = models.CharField(max_length=150, blank=True, default="")
    tipo = models.CharField(max_length=20, choices=TipoDrenaje)
    geom = models.MultiLineStringField(srid=4326)
    zona_influencia = models.MultiPolygonField(srid=4326, null=True, blank=True)
    # Calculada al importar: la cuenca con mayor longitud de intersección con el cauce.
    cuenca = models.ForeignKey(
        Cuenca, on_delete=models.PROTECT, null=True, blank=True, related_name="torrenteras"
    )

    class Meta:
        constraints = (
            UniqueConstraint(fields=["tipo", "id_origen"], name="territorio_torrentera_unica"),
            valor_en("tipo", TipoDrenaje.values),
        )

    def __str__(self):
        return f"{self.tipo} {self.id_origen} {self.nombre}".strip()


class UnidadTerritorialAbstracta(models.Model):
    """Una medición se refiere a una cuenca o a un distrito (restricción XOR en la base de datos).

    Las FK no crean índice propio: los índices únicos parciales de cada serie, con la unidad como
    primera columna, sirven también como índice de la FK.
    """

    cuenca = models.ForeignKey(
        Cuenca, on_delete=models.PROTECT, null=True, blank=True, db_index=False, related_name="+"
    )
    distrito = models.ForeignKey(
        Distrito, on_delete=models.PROTECT, null=True, blank=True, db_index=False, related_name="+"
    )

    class Meta:
        abstract = True
        constraints = (exactamente_una_unidad(),)
