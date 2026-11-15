import pytest
from django.contrib.gis.geos import LineString, MultiLineString, MultiPolygon, Point, Polygon
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient
from test_modelos import crear_cuenca, crear_distrito, crear_incidente, crear_torrentera

from territorio.models import Distrito

CAPA_PUBLICA_CON_UN_REGISTRO = {
    "distritos": lambda: crear_distrito(1),
    "cuencas": lambda: crear_cuenca("uh7", "8461"),
    "torrenteras": lambda: crear_torrentera("torrentera", "12"),
    "incidentes": lambda: crear_incidente("E-001"),
}

GEOMETRIA_POR_CAPA = {
    "distritos": "MultiPolygon",
    "cuencas": "MultiPolygon",
    "torrenteras": "MultiLineString",
    "incidentes": "Point",
}

RUTAS_DOCUMENTADAS = {"/healthz/"} | {
    ruta for capa in GEOMETRIA_POR_CAPA for ruta in (f"/api/v1/{capa}/", f"/api/v1/{capa}/{{id}}/")
}


@pytest.fixture
def cliente():
    return APIClient()


@pytest.fixture
def esquema(cliente):
    return cliente.get("/api/schema/", {"format": "json"}).json()


@pytest.mark.django_db
@pytest.mark.parametrize("capa", CAPA_PUBLICA_CON_UN_REGISTRO.keys())
def test_capas_publicas_devuelven_featurecollection_sin_paginar(cliente, capa):
    CAPA_PUBLICA_CON_UN_REGISTRO[capa]()
    cuerpo = cliente.get(f"/api/v1/{capa}/").json()

    assert set(cuerpo) == {"type", "features"}
    assert (cuerpo["type"], len(cuerpo["features"])) == ("FeatureCollection", 1)


# Más de seis decimales: la API debe redondear a 6 (unos 10 cm) y mantener el orden lon, lat.
CAJA_CON_MUCHOS_DECIMALES = (-66.1712345678, -17.4012345678, -66.1512345678, -17.3812345678)


@pytest.mark.django_db
def test_distritos_multipolygon_con_6_decimales_y_sin_campos_internos(cliente):
    Distrito.objects.create(
        codigo=3,
        nombre="Distrito 3",
        fuente_capa="capa_interna",
        atributos_origen={"OBJECTID": 7},
        geom=MultiPolygon(Polygon.from_bbox(CAJA_CON_MUCHOS_DECIMALES), srid=4326),
    )
    rasgo = cliente.get("/api/v1/distritos/").json()["features"][0]

    assert rasgo["geometry"]["type"] == "MultiPolygon"
    assert rasgo["geometry"]["coordinates"][0][0][0] == [-66.171235, -17.401235]
    assert set(rasgo["properties"]) == {"codigo", "nombre", "subalcaldia", "tipo_area"}


def valores_de(cliente, consulta) -> list[str]:
    capa, filtro = consulta
    rasgos = cliente.get(f"/api/v1/{capa}/", filtro).json()["features"]
    return [rasgo["properties"][campo] for rasgo in rasgos for campo in filtro]


@pytest.mark.django_db
def test_cuencas_y_torrenteras_filtran_por_capa_y_tipo(cliente):
    crear_cuenca("uh7", "1")
    crear_cuenca("uh8", "2")
    crear_torrentera("torrentera", "1")
    crear_torrentera("canal", "2")

    assert valores_de(cliente, ("cuencas", {"capa_origen": "uh8"})) == ["uh8"]
    assert valores_de(cliente, ("torrenteras", {"tipo": "canal"})) == ["canal"]


@pytest.mark.django_db
def test_incidentes_filtran_por_clase(cliente):
    crear_incidente("E-001")
    otro = crear_incidente("E-002")
    otro.clase = "otro"
    otro.save()

    assert valores_de(cliente, ("incidentes", {"clase": "otro"})) == ["otro"]


ESCRITURA_POR_METODO = {
    "POST": ("post", False),
    "PUT": ("put", True),
    "PATCH": ("patch", True),
    "DELETE": ("delete", True),
}


@pytest.mark.django_db
@pytest.mark.parametrize("caso", ESCRITURA_POR_METODO.values(), ids=ESCRITURA_POR_METODO.keys())
def test_api_rechaza_escritura(cliente, caso):
    metodo, en_detalle = caso
    distrito = crear_distrito(1)
    ruta = f"/api/v1/distritos/{distrito.pk}/" if en_detalle else "/api/v1/distritos/"

    assert getattr(cliente, metodo)(ruta, {}, format="json").status_code == 405


def test_esquema_y_swagger_responden_200(cliente):
    esquema = cliente.get("/api/schema/")
    swagger = cliente.get("/api/docs/")

    assert (esquema.status_code, swagger.status_code) == (200, 200)
    assert "jsdelivr" not in swagger.content.decode()


def resolver(esquema, nodo) -> dict:
    while "$ref" in nodo:
        nodo = esquema["components"]["schemas"][nodo["$ref"].rsplit("/", 1)[1]]
    return nodo


def tipo_de_geometria(esquema, capa) -> list[str]:
    detalle = esquema["paths"][f"/api/v1/{capa}/{{id}}/"]["get"]["responses"]["200"]
    rasgo = resolver(esquema, detalle["content"]["application/json"]["schema"])
    geometria = resolver(esquema, rasgo["properties"]["geometry"])
    return geometria["properties"]["type"]["enum"]


@pytest.mark.parametrize("capa", GEOMETRIA_POR_CAPA.keys())
def test_esquema_tipa_geometrias_multi_del_modelo(esquema, capa):
    assert tipo_de_geometria(esquema, capa) == [GEOMETRIA_POR_CAPA[capa]]


def test_esquema_documenta_todas_las_rutas(esquema):
    assert set(esquema["paths"]) == RUTAS_DOCUMENTADAS


@pytest.mark.parametrize("estado_http", ["200", "503"])
def test_esquema_enumera_los_estados_de_healthz(esquema, estado_http):
    respuesta = esquema["paths"]["/healthz/"]["get"]["responses"][estado_http]
    cuerpo = resolver(esquema, respuesta["content"]["application/json"]["schema"])
    estado = resolver(esquema, cuerpo["properties"]["estado"])

    assert estado["enum"] == ["ok", "no_disponible"]


@pytest.mark.parametrize("capa", GEOMETRIA_POR_CAPA.keys())
def test_esquema_agrupa_cada_capa_bajo_su_nombre(esquema, capa):
    assert esquema["paths"][f"/api/v1/{capa}/"]["get"]["tags"] == [capa]


PROPIEDADES_PUBLICAS_POR_CAPA = {
    "distritos": {"codigo", "nombre", "subalcaldia", "tipo_area"},
    "cuencas": {"capa_origen", "codigo", "nivel", "nombre"},
    "torrenteras": {"tipo", "id_origen", "nombre", "cuenca"},
    "incidentes": {"id_origen", "fecha", "clase", "distrito", "cuenca"},
}


@pytest.mark.django_db
@pytest.mark.parametrize("capa", PROPIEDADES_PUBLICAS_POR_CAPA.keys())
def test_capas_publicas_exponen_solo_sus_propiedades(cliente, capa):
    CAPA_PUBLICA_CON_UN_REGISTRO[capa]()
    rasgo = cliente.get(f"/api/v1/{capa}/").json()["features"][0]

    assert set(rasgo["properties"]) == PROPIEDADES_PUBLICAS_POR_CAPA[capa]


ESQUINA_X, ESQUINA_Y = CAJA_CON_MUCHOS_DECIMALES[:2]
GEOMETRIA_CON_MUCHOS_DECIMALES_POR_CAPA = {
    "distritos": MultiPolygon(Polygon.from_bbox(CAJA_CON_MUCHOS_DECIMALES), srid=4326),
    "cuencas": MultiPolygon(Polygon.from_bbox(CAJA_CON_MUCHOS_DECIMALES), srid=4326),
    "torrenteras": MultiLineString(
        LineString((ESQUINA_X, ESQUINA_Y), (-66.1512345678, -17.3812345678)), srid=4326
    ),
    "incidentes": Point(ESQUINA_X, ESQUINA_Y, srid=4326),
}


def primer_vertice(coordenadas) -> list[float]:
    while isinstance(coordenadas[0], list):
        coordenadas = coordenadas[0]
    return coordenadas


@pytest.mark.django_db
@pytest.mark.parametrize("capa", GEOMETRIA_CON_MUCHOS_DECIMALES_POR_CAPA.keys())
def test_capas_publicas_redondean_a_6_decimales_en_orden_lon_lat(cliente, capa):
    registro = CAPA_PUBLICA_CON_UN_REGISTRO[capa]()
    type(registro).objects.filter(pk=registro.pk).update(
        geom=GEOMETRIA_CON_MUCHOS_DECIMALES_POR_CAPA[capa]
    )
    rasgo = cliente.get(f"/api/v1/{capa}/").json()["features"][0]

    assert primer_vertice(rasgo["geometry"]["coordinates"]) == [-66.171235, -17.401235]


@pytest.mark.django_db
@pytest.mark.parametrize("capa", CAPA_PUBLICA_CON_UN_REGISTRO.keys())
def test_detalle_devuelve_un_feature_con_su_id(cliente, capa):
    registro = CAPA_PUBLICA_CON_UN_REGISTRO[capa]()
    rasgo = cliente.get(f"/api/v1/{capa}/{registro.pk}/").json()

    assert (rasgo["type"], rasgo["id"]) == ("Feature", registro.pk)


# Columnas pesadas que no se publican: la consulta del listado no debe leerlas.
COLUMNAS_NO_PUBLICADAS = ('"atributos_origen"', '"zona_influencia"', '"fuente_capa"')


@pytest.mark.django_db
@pytest.mark.parametrize("capa", CAPA_PUBLICA_CON_UN_REGISTRO.keys())
def test_listado_no_lee_columnas_no_publicadas(cliente, capa):
    CAPA_PUBLICA_CON_UN_REGISTRO[capa]()
    with CaptureQueriesContext(connection) as consultas:
        cliente.get(f"/api/v1/{capa}/")

    sql = " ".join(consulta["sql"] for consulta in consultas)
    assert [columna for columna in COLUMNAS_NO_PUBLICADAS if columna in sql] == []


def test_swagger_carga_los_recursos_del_sidecar(cliente):
    html = cliente.get("/api/docs/").content.decode()

    assert "drf_spectacular_sidecar/swagger-ui-dist/swagger-ui-bundle.js" in html
