from pathlib import PureWindowsPath

from django.contrib.gis.db import models
from django.core.exceptions import ValidationError
from django.db.models import CheckConstraint, Q, UniqueConstraint

from territorio.restricciones import valor_en


def validar_ruta_relativa(ruta: str) -> None:
    """La ruta se resuelve bajo el directorio de datos: ni absoluta ni con saltos hacia arriba.

    PureWindowsPath reconoce tanto «/» como «\\», unidades («C:») y rutas UNC.
    """
    ruta_windows = PureWindowsPath(ruta)
    if ruta_windows.drive or ruta_windows.root or ".." in ruta_windows.parts:
        raise ValidationError(
            "Use una ruta relativa al directorio de datos, sin unidad ni «..».",
            code="ruta_no_relativa",
        )


class Polarizacion(models.TextChoices):
    VV = "VV", "VV"
    VH = "VH", "VH"


class ProveedorSAR(models.TextChoices):
    CDSE = "cdse", "Copernicus Data Space Ecosystem"
    ASF = "asf", "Alaska Satellite Facility"
    MPC = "mpc", "Microsoft Planetary Computer"


class PasoOrbita(models.TextChoices):
    ASCENDENTE = "ASC", "Ascendente"
    DESCENDENTE = "DESC", "Descendente"


class EscenaSAR(models.Model):
    """Una escena Sentinel-1 por polarización; el ráster vive en disco, aquí solo su ruta."""

    id_producto = models.CharField(max_length=200)
    polarizacion = models.CharField(max_length=20, choices=Polarizacion)
    proveedor = models.CharField(max_length=20, choices=ProveedorSAR)
    tipo_producto = models.CharField(max_length=20)
    plataforma = models.CharField(max_length=20)
    fecha_adquisicion = models.DateTimeField()
    paso_orbita = models.CharField(max_length=20, choices=PasoOrbita)
    orbita_relativa = models.PositiveSmallIntegerField()
    huella = models.PolygonField(srid=4326)
    ruta_archivo = models.CharField(max_length=500, validators=[validar_ruta_relativa])
    registrado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = (
            UniqueConstraint(
                fields=["id_producto", "polarizacion"],
                name="radar_escenasar_unica_por_producto_y_polarizacion",
            ),
            valor_en("polarizacion", Polarizacion.values),
            valor_en("proveedor", ProveedorSAR.values),
            valor_en("paso_orbita", PasoOrbita.values),
            CheckConstraint(
                condition=Q(orbita_relativa__gte=1), name="radar_escenasar_orbita_relativa_positiva"
            ),
        )

    def __str__(self):
        return f"{self.id_producto} {self.polarizacion}"
