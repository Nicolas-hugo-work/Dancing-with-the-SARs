from django.db import models

from territorio.models import Cuenca, Distrito, UnidadTerritorialAbstracta
from territorio.restricciones import entre, posterior, unica_por_unidad, valor_en


class NivelAlerta(models.TextChoices):
    VERDE = "verde", "Verde"
    AMARILLA = "amarilla", "Amarilla"
    NARANJA = "naranja", "Naranja"
    ROJA = "roja", "Roja"


class TipoIndice(models.TextChoices):
    AMENAZA = "amenaza", "Amenaza"
    RIESGO = "riesgo", "Riesgo"


class IndiceRiesgo(UnidadTerritorialAbstracta):
    tipo = models.CharField(max_length=20, choices=TipoIndice)
    fecha_hora_ref = models.DateTimeField()
    valor = models.FloatField()
    nivel = models.CharField(max_length=20, choices=NivelAlerta)
    version_metodo = models.CharField(max_length=30)
    componentes = models.JSONField(default=dict, blank=True)
    calculado_en = models.DateTimeField(auto_now_add=True)

    class Meta(UnidadTerritorialAbstracta.Meta):
        constraints = (
            *UnidadTerritorialAbstracta.Meta.constraints,
            *unica_por_unidad("tipo", "fecha_hora_ref", "version_metodo"),
            entre("valor", (0, 1)),
            valor_en("tipo", TipoIndice.values),
            valor_en("nivel", NivelAlerta.values),
        )

    def __str__(self):
        return f"{self.tipo} {self.fecha_hora_ref:%Y-%m-%d %H:%M} {self.nivel}"


class TipoAmenaza(models.TextChoices):
    INUNDACION = "inundacion", "Inundación"
    RIADA_MAZAMORRA = "riada_mazamorra", "Riada o mazamorra"


class OrigenAlerta(models.TextChoices):
    MODELO_SAT = "modelo_sat", "Modelo del SAT"
    SENAMHI = "senamhi", "SENAMHI"
    GAMC = "gamc", "GAMC"


class EstadoAlerta(models.TextChoices):
    PROPUESTA = "propuesta", "Propuesta"
    EMITIDA = "emitida", "Emitida"
    ACTUALIZADA = "actualizada", "Actualizada"
    CANCELADA = "cancelada", "Cancelada"
    EXPIRADA = "expirada", "Expirada"


class Alerta(models.Model):
    """El sistema solo propone alertas; las declara la autoridad competente (Ley 602, art. 38)."""

    nivel = models.CharField(max_length=20, choices=NivelAlerta)
    amenaza = models.CharField(max_length=20, choices=TipoAmenaza)
    distrito = models.ForeignKey(Distrito, on_delete=models.PROTECT, related_name="alertas")
    cuenca = models.ForeignKey(
        Cuenca, on_delete=models.PROTECT, null=True, blank=True, related_name="alertas"
    )
    emitida_en = models.DateTimeField(null=True, blank=True)
    vigente_desde = models.DateTimeField()
    vigente_hasta = models.DateTimeField()
    origen = models.CharField(max_length=20, choices=OrigenAlerta)
    indice = models.ForeignKey(
        IndiceRiesgo, on_delete=models.PROTECT, null=True, blank=True, related_name="alertas"
    )
    nivel_fuente_original = models.CharField(max_length=50, blank=True, default="")
    emisor = models.CharField(max_length=100, blank=True, default="")
    estado = models.CharField(
        max_length=20,
        choices=EstadoAlerta,
        default=EstadoAlerta.PROPUESTA,
        db_default=EstadoAlerta.PROPUESTA,
    )
    acciones_recomendadas = models.TextField(blank=True, default="")
    # PROTECT y no SET_NULL: las alertas se cancelan, no se borran, y la cadena queda trazable.
    reemplaza = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reemplazada_por",
    )

    class Meta:
        constraints = (
            valor_en("nivel", NivelAlerta.values),
            valor_en("amenaza", TipoAmenaza.values),
            valor_en("origen", OrigenAlerta.values),
            valor_en("estado", EstadoAlerta.values),
            posterior("vigente_hasta", "vigente_desde"),
            models.CheckConstraint(
                condition=(
                    ~models.Q(estado=EstadoAlerta.EMITIDA) | models.Q(emitida_en__isnull=False)
                ),
                name="riesgo_alerta_emitida_tiene_emitida_en",
                violation_error_message="Una alerta emitida debe registrar cuándo se emitió.",
            ),
            models.CheckConstraint(
                condition=~models.Q(reemplaza=models.F("id")),
                name="riesgo_alerta_no_se_reemplaza_a_si_misma",
            ),
        )

    def __str__(self):
        return f"{self.nivel} {self.amenaza} {self.vigente_desde:%Y-%m-%d %H:%M} ({self.estado})"
