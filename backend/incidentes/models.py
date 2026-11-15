from django.contrib.gis.db import models
from django.db.models import UniqueConstraint

from territorio.models import Cuenca, Distrito, ImportadoAbstracto
from territorio.restricciones import valor_en


class ClaseIncidente(models.TextChoices):
    INUNDACION = "inundacion", "Inundación"
    RIADA_MAZAMORRA = "riada_mazamorra", "Riada o mazamorra"
    OTRO = "otro", "Otro"


class ConjuntoIncidente(models.TextChoices):
    CALIBRACION = "calibracion", "Calibración"
    VALIDACION = "validacion", "Validación"


class Incidente(ImportadoAbstracto):
    id_origen = models.CharField(max_length=64)
    # Fecha y hora tal como las registra la fuente, sin conversión; su zona horaria está pendiente
    # de confirmar con el GAMC (README, «Decisiones de esquema»).
    fecha = models.DateField()
    hora = models.TimeField(null=True, blank=True)
    tipo_evento_origen = models.CharField(max_length=100)
    clase = models.CharField(max_length=20, choices=ClaseIncidente)
    geom = models.PointField(srid=4326)
    # Calculadas al importar por punto en polígono.
    distrito = models.ForeignKey(
        Distrito, on_delete=models.PROTECT, null=True, blank=True, related_name="incidentes"
    )
    cuenca = models.ForeignKey(
        Cuenca, on_delete=models.PROTECT, null=True, blank=True, related_name="incidentes"
    )
    personas_afectadas = models.PositiveIntegerField(null=True, blank=True)
    viviendas_afectadas = models.PositiveIntegerField(null=True, blank=True)
    conjunto = models.CharField(max_length=20, choices=ConjuntoIncidente, blank=True, default="")

    class Meta:
        constraints = (
            UniqueConstraint(fields=["id_origen"], name="incidentes_incidente_id_origen_unico"),
            valor_en("clase", ClaseIncidente.values),
            valor_en("conjunto", [*ConjuntoIncidente.values, ""]),
        )

    def __str__(self):
        return f"{self.id_origen} {self.fecha:%Y-%m-%d} {self.clase}"
