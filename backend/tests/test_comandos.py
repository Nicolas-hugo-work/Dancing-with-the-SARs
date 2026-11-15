import json
import re
from datetime import date, datetime
from io import StringIO
from pathlib import Path

import pytest
from django.contrib.gis.geos import MultiPolygon, Polygon
from django.core.management import CommandError, call_command
from test_importacion import CAJA_DISTRITO_1, FIXTURES, escribir_geojson, shapefile_desde
from test_modelos import crear_incidente

from incidentes.importacion import clase_desde_tipo, fecha_desde_origen
from incidentes.models import Incidente
from territorio.errores import ImportacionError
from territorio.models import Distrito, Torrentera

DISTRITOS_DE_EJEMPLO = FIXTURES / "distritos_min.geojson"
CUENCAS_DE_EJEMPLO = FIXTURES / "cuencas_min.geojson"


def ejecutar(comando: str, *argumentos, **opciones) -> str:
    salida = StringIO()
    call_command(comando, *argumentos, stdout=salida, **opciones)
    return salida.getvalue()


@pytest.mark.django_db
def test_importar_territorio_desde_geojson_informa_resumen():
    salida = ejecutar("importar_territorio", "distritos", archivo=DISTRITOS_DE_EJEMPLO)

    assert salida.strip() == "distritos: 2 creados, 0 actualizados, 0 geometrías reparadas"


FUENTE_O_CAPA_INVALIDA = {
    "sin_fuente": (("distritos",), {}, "--archivo"),
    "capa_desconocida": (("barrios",), {"archivo": DISTRITOS_DE_EJEMPLO}, "invalid choice"),
}


@pytest.mark.parametrize("caso", FUENTE_O_CAPA_INVALIDA.values(), ids=FUENTE_O_CAPA_INVALIDA.keys())
def test_importar_exige_una_sola_fuente_y_capa_valida(caso):
    argumentos, opciones, mensaje = caso

    with pytest.raises(CommandError, match=mensaje):
        ejecutar("importar_territorio", *argumentos, **opciones)


def shapefile_en_utm_sin_prj(directorio: Path) -> Path:
    """Un distrito en UTM 19 S, en un Shapefile sin .prj y con un nombre de campo abreviado."""
    distrito = MultiPolygon(Polygon.from_bbox(CAJA_DISTRITO_1), srid=4326).transform(
        32719, clone=True
    )
    propiedades = {"DISTRITO": "D1", "NOM_DISTRI": "Uno"}
    geojson = escribir_geojson(
        directorio / "utm.geojson", [(propiedades, json.loads(distrito.json))]
    )
    shapefile = shapefile_desde(geojson, directorio / "shp" / "distritos.shp")
    shapefile.with_suffix(".prj").unlink()
    return shapefile


@pytest.mark.django_db
def test_shapefile_sin_prj_exige_srid_y_admite_campo(tmp_path):
    shapefile = shapefile_en_utm_sin_prj(tmp_path)

    with pytest.raises(CommandError, match="indique --srid"):
        ejecutar("importar_territorio", "distritos", archivo=shapefile)
    ejecutar(
        "importar_territorio",
        "distritos",
        archivo=shapefile,
        srid=32719,
        campo=["nombre=NOM_DISTRI"],
    )
    assert list(Distrito.objects.values_list("codigo", "nombre")) == [(1, "Uno")]


@pytest.mark.django_db
def test_importar_torrenteras_asigna_cuenca(tmp_path):
    ejecutar("importar_territorio", "cuencas_uh8", archivo=CUENCAS_DE_EJEMPLO)
    cauce = {"type": "MultiLineString", "coordinates": [[[-66.169, -17.39], [-66.152, -17.39]]]}
    propiedades = {"ID": "T-1", "NOMBRE": "Torrentera sintetica"}
    torrenteras = escribir_geojson(tmp_path / "torrenteras.geojson", [(propiedades, cauce)])

    ejecutar("importar_territorio", "torrenteras", archivo=torrenteras)

    assert list(Torrentera.objects.values_list("id_origen", "tipo", "cuenca__codigo")) == [
        ("T-1", "torrentera", "8461")
    ]


CLASE_POR_TIPO_DE_EVENTO = {
    "con_tilde_y_mayusculas": ("INUNDACIÓN", "inundacion"),
    "con_espacios_y_detalle": ("  Inundación por desborde ", "inundacion"),
    "riada": ("Riada", "riada_mazamorra"),
    "mazamorra": ("mazamorra", "riada_mazamorra"),
    "otro_evento": ("Deslizamiento", "otro"),
}


@pytest.mark.parametrize(
    "caso", CLASE_POR_TIPO_DE_EVENTO.values(), ids=CLASE_POR_TIPO_DE_EVENTO.keys()
)
def test_clase_desde_tipo_normaliza_tildes_y_mayusculas(caso):
    tipo_de_evento, clase = caso

    assert clase_desde_tipo(tipo_de_evento) == clase


# La fecha es la que escribió la fuente: las 23:30 del día 10 en -04:00 no pasan al día 11 en UTC.
FECHA_POR_VALOR_DE_ORIGEN = {
    "fecha_y_hora_con_zona": ("2024-02-10T23:30:00-04:00", date(2024, 2, 10)),
    "solo_fecha": (" 2024-02-10 ", date(2024, 2, 10)),
    "fecha_tipada": (date(2024, 2, 10), date(2024, 2, 10)),
    "fecha_y_hora_tipadas": (datetime(2024, 2, 10, 23, 30), date(2024, 2, 10)),
}


@pytest.mark.parametrize(
    "caso", FECHA_POR_VALOR_DE_ORIGEN.values(), ids=FECHA_POR_VALOR_DE_ORIGEN.keys()
)
def test_fecha_desde_origen_no_desplaza_zona(caso):
    valor, fecha = caso

    assert fecha_desde_origen(valor) == fecha


@pytest.mark.parametrize(
    "valor",
    [
        "10/02/2024",
        "2024-13-40",
        "2024-13-40T23:30:00-04:00",
        " 2024-13-40 ",
        "2024-02-10 sin hora",
        "2024-02-10T25",
        "",
        None,
    ],
)
def test_fecha_desde_origen_rechaza_lo_que_no_es_una_fecha(valor):
    with pytest.raises(ImportacionError, match=re.escape(repr(valor))):
        fecha_desde_origen(valor)


INCIDENTES_DE_EJEMPLO = FIXTURES / "incidentes_min.geojson"


@pytest.fixture
def territorio_de_ejemplo():
    ejecutar("importar_territorio", "distritos", archivo=DISTRITOS_DE_EJEMPLO)
    ejecutar("importar_territorio", "cuencas_uh8", archivo=CUENCAS_DE_EJEMPLO)


@pytest.mark.django_db
@pytest.mark.usefixtures("territorio_de_ejemplo")
def test_importar_incidentes_asigna_distrito_y_cuenca_por_ubicacion():
    ejecutar("importar_incidentes", archivo=INCIDENTES_DE_EJEMPLO)

    campos = ("id_origen", "fecha", "clase", "distrito__codigo", "cuenca__codigo")
    assert list(Incidente.objects.order_by("id_origen").values_list(*campos)) == [
        ("E-001", date(2024, 2, 10), "inundacion", 1, "8461"),
        ("E-002", date(2024, 2, 11), "riada_mazamorra", 2, "8462"),
        ("E-003", date(2024, 2, 12), "riada_mazamorra", None, None),
    ]
    # La procedencia conserva la fecha y hora con su zona, tal como llegó.
    origen = Incidente.objects.get(id_origen="E-002").atributos_origen
    assert origen["FECHA"] == "2024-02-11T23:30:00-04:00"


@pytest.mark.django_db
@pytest.mark.usefixtures("territorio_de_ejemplo")
def test_incidente_fuera_de_cercado_se_informa_sin_distrito():
    crear_incidente("E-900")  # sin distrito, de una carga anterior: no es de esta importación

    salida = ejecutar("importar_incidentes", archivo=INCIDENTES_DE_EJEMPLO)

    assert salida.splitlines()[-1] == "sin distrito (fuera de los distritos cargados): E-003"


@pytest.mark.django_db
def test_importar_incidentes_desde_geojson_es_idempotente():
    ejecutar("importar_incidentes", archivo=INCIDENTES_DE_EJEMPLO)
    salida = ejecutar("importar_incidentes", archivo=INCIDENTES_DE_EJEMPLO)

    assert salida.splitlines()[0] == "incidentes: 0 creados, 3 actualizados, 0 geometrías reparadas"
    assert Incidente.objects.count() == 3


@pytest.mark.django_db
def test_reimportar_incidentes_recalcula_distrito_y_cuenca():
    ejecutar("importar_incidentes", archivo=INCIDENTES_DE_EJEMPLO)
    ejecutar("importar_territorio", "distritos", archivo=DISTRITOS_DE_EJEMPLO)
    ejecutar("importar_territorio", "cuencas_uh8", archivo=CUENCAS_DE_EJEMPLO)

    ejecutar("importar_incidentes", archivo=INCIDENTES_DE_EJEMPLO)

    asignados = Incidente.objects.get(id_origen="E-001")
    assert (asignados.distrito.codigo, asignados.cuenca.codigo) == (1, "8461")
