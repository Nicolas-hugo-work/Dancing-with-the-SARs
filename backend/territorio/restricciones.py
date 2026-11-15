"""Restricciones de base de datos que comparten las mediciones de todas las apps."""

from collections.abc import Iterable

from django.db.models import CheckConstraint, F, Q, UniqueConstraint

UNIDADES = ("cuenca", "distrito")


def exactamente_una_unidad() -> CheckConstraint:
    """Exige que la medición pertenezca a una cuenca o a un distrito, nunca a ambos ni a ninguno."""
    return CheckConstraint(
        condition=(
            Q(cuenca__isnull=False, distrito__isnull=True)
            | Q(cuenca__isnull=True, distrito__isnull=False)
        ),
        name="%(app_label)s_%(class)s_unidad_exactamente_una",
        violation_error_message="Indique exactamente una unidad territorial: cuenca o distrito.",
    )


def valor_en(campo: str, valores: Iterable[str | int]) -> CheckConstraint:
    """Catálogo cerrado en la base; `choices` solo se valida en formularios y full_clean."""
    return CheckConstraint(
        condition=Q(**{f"{campo}__in": list(valores)}),
        name=f"%(app_label)s_%(class)s_{campo}_valido",
    )


def posterior(fin: str, inicio: str) -> CheckConstraint:
    """`fin` es estrictamente posterior a `inicio`: un período nunca dura cero."""
    return CheckConstraint(
        condition=Q(**{f"{fin}__gt": F(inicio)}),
        name=f"%(app_label)s_%(class)s_{fin}_posterior_a_{inicio}",
    )


def entre(campo: str, rango: tuple[float, float]) -> CheckConstraint:
    """Rango cerrado. BETWEEN también rechaza NaN e infinito, que un FloatField sí admite."""
    return CheckConstraint(
        condition=Q(**{f"{campo}__range": rango}),
        name=f"%(app_label)s_%(class)s_{campo}_en_rango",
    )


def unica_por_unidad(*campos: str) -> list[UniqueConstraint]:
    """Un único registro por unidad territorial y por los campos dados.

    Un UNIQUE sobre (cuenca, distrito, ...) no detecta duplicados porque la unidad vacía es NULL
    y NULL nunca es igual a NULL. Por eso hay un índice parcial por unidad, con ella como primera
    columna, que además sirve de índice de su FK.
    """
    return [
        UniqueConstraint(
            fields=[unidad, *campos],
            condition=Q(**{f"{unidad}__isnull": False}),
            name=f"%(app_label)s_%(class)s_unica_por_{unidad}",
        )
        for unidad in UNIDADES
    ]
