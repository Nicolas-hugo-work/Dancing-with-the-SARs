import json
import os
import re
import subprocess
from datetime import date
from pathlib import Path

import pytest
from django.contrib.gis.db.models.functions import NumGeometries
from django.contrib.gis.gdal import OGRGeometry
from django.contrib.gis.geos import LineString, MultiLineString, MultiPolygon, Point, Polygon
from django.db import DatabaseError
from django.db.models import Sum, UniqueConstraint

from incidentes.importacion import CAPA_INCIDENTES
from incidentes.models import Incidente
from territorio.errores import ImportacionError
from territorio.espacial import (
    cuenca_de_mayor_interseccion,
    cuenca_que_contiene,
    distrito_que_contiene,
)
from territorio.geometria import Normalizacion
from territorio.importacion import (
    CAPAS,
    OPCION_FECHAS_COMO_TEXTO,
    Capa,
    Entidad,
    Importacion,
    Origen,
    Resumen,
    entero,
    leer_archivo,
    mapear,
    parsear_mapeo,
    texto,
)
from territorio.models import Cuenca, Distrito

CUADRADO_EN_CERCADO = (
    "POLYGON((-66.17 -17.40, -66.15 -17.40, -66.15 -17.38, -66.17 -17.38, -66.17 -17.40))"
)
LINEA_EN_CERCADO = "LINESTRING(-66.17 -17.40, -66.15 -17.38)"


def ogr(wkt: str, srs: int | str | None = 4326) -> OGRGeometry:
    return OGRGeometry(wkt, srs=srs)


# Las curvas (GeoPackage o geodatabase con arcos) se pasan a líneas rectas: GEOS no las admite.
SIMPLE_O_CURVA_Y_SU_TIPO_MULTIPLE = {
    "poligono": (CUADRADO_EN_CERCADO, MultiPolygon),
    "linea": (LINEA_EN_CERCADO, MultiLineString),
    "multisuperficie": (
        "MULTISURFACE(((-66.17 -17.40, -66.15 -17.40, -66.15 -17.38, -66.17 -17.38,"
        " -66.17 -17.40)))",
        MultiPolygon,
    ),
    "poligono_curvo": (
        "CURVEPOLYGON(CIRCULARSTRING(-66.17 -17.39, -66.16 -17.38, -66.15 -17.39,"
        " -66.16 -17.40, -66.17 -17.39))",
        MultiPolygon,
    ),
    "multicurva": ("MULTICURVE((-66.17 -17.40, -66.15 -17.38))", MultiLineString),
}


@pytest.mark.parametrize(
    "caso",
    SIMPLE_O_CURVA_Y_SU_TIPO_MULTIPLE.values(),
    ids=SIMPLE_O_CURVA_Y_SU_TIPO_MULTIPLE.keys(),
)
def test_normalizar_promueve_a_multi(caso):
    wkt, tipo = caso
    geom, reparada = Normalizacion(tipo).normalizar(ogr(wkt))

    assert (type(geom), geom.srid, len(geom), reparada) == (tipo, 4326, 1, False)


# El mismo punto de Cercado (-66.16, -17.39) en UTM 19 S y en 4326 con altura.
PUNTO_EN_CERCADO = (-66.16, -17.39)
PUNTO_CON_SRID = {
    "utm_19s": ("POINT(801768.7727066388 8075063.815507382)", 32719),
    "con_altura": ("POINT Z(-66.16 -17.39 2550)", 4326),
}


@pytest.mark.parametrize("caso", PUNTO_CON_SRID.values(), ids=PUNTO_CON_SRID.keys())
def test_normalizar_transforma_a_4326_en_orden_lon_lat(caso):
    wkt, srid = caso
    geom, _ = Normalizacion(Point).normalizar(ogr(wkt, srid))

    assert (geom.srid, geom.hasz) == (4326, False)
    assert geom.coords == pytest.approx(PUNTO_EN_CERCADO, abs=1e-6)


def test_normalizar_sin_crs_usa_srid_indicado_o_falla():
    sin_crs = ogr(PUNTO_CON_SRID["utm_19s"][0], srs=None)
    geom, _ = Normalizacion(Point, srid_indicado=32719).normalizar(sin_crs)

    assert geom.coords == pytest.approx(PUNTO_EN_CERCADO, abs=1e-6)
    # La misma geometría sigue sin CRS: normalizar no modifica su entrada.
    with pytest.raises(ImportacionError, match="indique --srid"):
        Normalizacion(Point).normalizar(sin_crs)


def test_normalizar_prefiere_srid_indicado_a_un_srs_implicito():
    # GDAL supone EPSG:4326 en un GeoJSON sin «crs» (RFC 7946), aunque las coordenadas sean UTM.
    utm_supuesto_4326 = ogr(PUNTO_CON_SRID["utm_19s"][0], 4326)

    geom, _ = Normalizacion(Point, srid_indicado=32719).normalizar(
        utm_supuesto_4326, srs_implicito=True
    )

    assert geom.coords == pytest.approx(PUNTO_EN_CERCADO, abs=1e-6)
    # Sin --srid el supuesto vale como declarado: aquí deja el punto fuera del municipio.
    with pytest.raises(ImportacionError, match="fuera de la extensión"):
        Normalizacion(Point).normalizar(utm_supuesto_4326, srs_implicito=True)


def test_normalizacion_rechaza_srid_indicado_desconocido():
    with pytest.raises(ImportacionError, match="--srid 99999 no es un código EPSG conocido"):
        Normalizacion(Point, srid_indicado=99999)


# Proyección válida para GDAL pero sin código EPSG: no puede compararse con --srid.
TRANSVERSA_SIN_CODIGO_EPSG = "+proj=tmerc +lon_0=-66 +k=1 +x_0=500000 +ellps=WGS84 +units=m"
SRS_DECLARADO_INCOMPATIBLE_CON_32719 = {
    "otro_epsg": (4326, "contradice"),
    "sin_codigo_epsg": (TRANSVERSA_SIN_CODIGO_EPSG, "omita --srid"),
}


@pytest.mark.parametrize(
    "caso",
    SRS_DECLARADO_INCOMPATIBLE_CON_32719.values(),
    ids=SRS_DECLARADO_INCOMPATIBLE_CON_32719.keys(),
)
def test_normalizar_rechaza_srid_indicado_contradictorio(caso):
    srs_declarado, mensaje = caso
    geom = ogr("POINT(-66.16 -17.39)", srs_declarado)

    with pytest.raises(ImportacionError, match=mensaje):
        Normalizacion(Point, srid_indicado=32719).normalizar(geom)


@pytest.mark.parametrize("srid_declarado", [4326, 4979], ids=["mismo", "wgs84_3d"])
def test_normalizar_acepta_srid_indicado_con_la_misma_horizontal(srid_declarado):
    geom, _ = Normalizacion(Point, srid_indicado=4326).normalizar(
        ogr("POINT(-66.16 -17.39)", srid_declarado)
    )

    assert geom.coords == pytest.approx(PUNTO_EN_CERCADO, abs=1e-6)


# Polígonos inválidos y un punto que la reparación debe conservar dentro de la superficie.
INVALIDA_Y_PUNTO_INTERIOR = {
    "lazo": (
        "POLYGON((-66.17 -17.40, -66.15 -17.38, -66.15 -17.40, -66.17 -17.38, -66.17 -17.40))",
        (-66.168, -17.39),
    ),
    "espiga": (
        "POLYGON((-66.20 -17.40, -66.18 -17.40, -66.18 -17.38, -66.20 -17.38, -66.20 -17.40,"
        " -66.25 -17.40, -66.20 -17.40))",
        (-66.19, -17.39),
    ),
    "partes_solapadas": (
        "MULTIPOLYGON("
        "((-66.20 -17.40, -66.18 -17.40, -66.18 -17.38, -66.20 -17.38, -66.20 -17.40)),"
        " ((-66.19 -17.39, -66.17 -17.39, -66.17 -17.37, -66.19 -17.37, -66.19 -17.39)))",
        (-66.185, -17.385),
    ),
}


@pytest.mark.parametrize(
    "caso", INVALIDA_Y_PUNTO_INTERIOR.values(), ids=INVALIDA_Y_PUNTO_INTERIOR.keys()
)
def test_normalizar_repara_invalida_y_lo_informa(caso):
    wkt, punto_interior = caso
    geom, reparada = Normalizacion(MultiPolygon).normalizar(ogr(wkt))

    assert (type(geom), geom.valid, reparada) == (MultiPolygon, True, True)
    assert geom.covers(Point(*punto_interior, srid=4326))


TIPO_INCOMPATIBLE_CON_SU_CAPA = {
    "punto_en_capa_de_superficies": ("POINT(-66.16 -17.39)", MultiPolygon),
    "multipunto_de_dos_partes": ("MULTIPOINT((-66.16 -17.39), (-66.17 -17.38))", Point),
}


@pytest.mark.parametrize(
    "caso", TIPO_INCOMPATIBLE_CON_SU_CAPA.values(), ids=TIPO_INCOMPATIBLE_CON_SU_CAPA.keys()
)
def test_normalizar_rechaza_tipo_incompatible(caso):
    wkt, tipo = caso

    with pytest.raises(ImportacionError, match="tipo incompatible"):
        Normalizacion(tipo).normalizar(ogr(wkt))


def test_normalizar_reduce_multipunto_de_una_parte():
    geom, _ = Normalizacion(Point).normalizar(ogr("MULTIPOINT((-66.16 -17.39))"))

    assert (type(geom), geom.srid, geom.coords) == (Point, 4326, PUNTO_EN_CERCADO)


FUERA_DE_LA_EXTENSION_DEL_MUNICIPIO = {
    "la_paz": "POINT(-68.13 -16.50)",
    "ejes_invertidos": "POINT(-17.39 -66.16)",
}


@pytest.mark.parametrize(
    "wkt",
    FUERA_DE_LA_EXTENSION_DEL_MUNICIPIO.values(),
    ids=FUERA_DE_LA_EXTENSION_DEL_MUNICIPIO.keys(),
)
def test_normalizar_rechaza_fuera_de_extension_y_ejes_invertidos(wkt):
    with pytest.raises(ImportacionError, match="fuera de la extensión"):
        Normalizacion(Point).normalizar(ogr(wkt))


SIN_GEOMETRIA_Y_TIPO_DE_CAPA = {
    "nula": (None, MultiPolygon),
    "punto_vacio": (ogr("POINT EMPTY"), MultiPolygon),
    "multipoligono_vacio": (ogr("MULTIPOLYGON EMPTY"), MultiPolygon),
    # OGR no lo considera vacío, pero GEOS lo lee como POINT EMPTY.
    "punto_nan": (ogr("POINT(nan nan)"), Point),
}


@pytest.mark.parametrize(
    "caso", SIN_GEOMETRIA_Y_TIPO_DE_CAPA.values(), ids=SIN_GEOMETRIA_Y_TIPO_DE_CAPA.keys()
)
def test_normalizar_rechaza_entidad_sin_geometria(caso):
    geom, tipo = caso

    with pytest.raises(ImportacionError, match="sin geometría"):
        Normalizacion(tipo).normalizar(geom)


COORDENADA_NO_FINITA_Y_TIPO_DE_CAPA = {
    "punto": (Point(-66.16, float("inf"), srid=4326).ogr, Point),
    "superficie": (
        Polygon(
            ((-66.17, -17.40), (-66.15, float("inf")), (-66.15, -17.38), (-66.17, -17.40)),
            srid=4326,
        ).ogr,
        MultiPolygon,
    ),
}


@pytest.mark.parametrize(
    "caso",
    COORDENADA_NO_FINITA_Y_TIPO_DE_CAPA.values(),
    ids=COORDENADA_NO_FINITA_Y_TIPO_DE_CAPA.keys(),
)
def test_normalizar_rechaza_coordenadas_no_finitas(caso):
    geom, tipo = caso

    with pytest.raises(ImportacionError, match="coordenadas no finitas"):
        Normalizacion(tipo).normalizar(geom)


def test_normalizar_no_repara_capas_de_puntos():
    punto_y_lazo = ogr(
        "GEOMETRYCOLLECTION(POINT(-66.16 -17.39), POLYGON((-66.17 -17.40, -66.15 -17.38,"
        " -66.15 -17.40, -66.17 -17.38, -66.17 -17.40)))"
    )

    with pytest.raises(ImportacionError, match="geometría inválida en una capa de Point"):
        Normalizacion(Point).normalizar(punto_y_lazo)


TRANSFORMACION_IMPOSIBLE = {
    "con_codigo_epsg": (32719, "desde EPSG:32719"),
    "sin_codigo_epsg": (TRANSVERSA_SIN_CODIGO_EPSG, "desde el sistema declarado"),
}


@pytest.mark.parametrize(
    "caso", TRANSFORMACION_IMPOSIBLE.values(), ids=TRANSFORMACION_IMPOSIBLE.keys()
)
def test_normalizar_informa_transformacion_imposible(caso):
    srs_declarado, origen = caso
    fuera_del_dominio_de_la_proyeccion = ogr("POINT(1e12 1e12)", srs_declarado)

    with pytest.raises(ImportacionError, match=f"no se pudo transformar {origen}"):
        Normalizacion(Point).normalizar(fuera_del_dominio_de_la_proyeccion)


# OGR entrega reales en los campos Double de un DBF: 8461.0 debe ser el código "8461", no "8461.0".
CONVERSION_DE_VALOR_DE_ORIGEN = {
    "texto_nulo": (texto, None, ""),
    "texto_con_espacios": (texto, "  Tunari ", "Tunari"),
    "texto_de_real_entero": (texto, 8461.0, "8461"),
    "texto_de_entero": (texto, 8461, "8461"),
    "texto_de_real": (texto, 7.25, "7.25"),
    "entero": (entero, 7, 7),
    "entero_de_real_entero": (entero, 7.0, 7),
    "entero_con_prefijo": (entero, "D7", 7),
    "entero_con_palabra": (entero, "Distrito 7", 7),
    "entero_con_espacios": (entero, " 12 ", 12),
}


@pytest.mark.parametrize(
    "caso", CONVERSION_DE_VALOR_DE_ORIGEN.values(), ids=CONVERSION_DE_VALOR_DE_ORIGEN.keys()
)
def test_conversores_entero_y_texto(caso):
    conversor, valor, esperado = caso

    assert conversor(valor) == esperado


VALOR_NO_CONVERTIBLE = {
    "entero_de_real": (entero, 7.5),
    "entero_de_texto_decimal": (entero, "7.5"),
    "entero_con_sufijo": (entero, "D7A"),
    "entero_vacio": (entero, ""),
    "entero_nulo": (entero, None),
    "entero_de_booleano": (entero, True),
    # Más dígitos de los que int() convierte por defecto (límite de Python 3.11+: 4300).
    "entero_demasiado_largo": (entero, "D" + "1" * 4301),
    "texto_de_real_no_finito": (texto, float("nan")),
}


@pytest.mark.parametrize("caso", VALOR_NO_CONVERTIBLE.values(), ids=VALOR_NO_CONVERTIBLE.keys())
def test_conversores_rechazan_valores_no_convertibles(caso):
    conversor, valor = caso

    with pytest.raises(ImportacionError, match=re.escape(repr(valor))):
        conversor(valor)


# Capas de prueba: el catálogo real de CAPAS tiene su propia prueba de coherencia.
DISTRITOS_DE_PRUEBA = Capa(
    nombre="distritos",
    modelo=Distrito,
    claves=("codigo",),
    campos={"codigo": Origen("DISTRITO", entero), "nombre": Origen("NOMBRE")},
    tipo_geom=MultiPolygon,
)
CUENCAS_UH7_DE_PRUEBA = Capa(
    nombre="cuencas_uh7",
    modelo=Cuenca,
    claves=("capa_origen", "codigo"),
    campos={"codigo": Origen("CODIGO"), "nombre": Origen("NOMBRE")},
    tipo_geom=MultiPolygon,
    fijos={"capa_origen": "uh7", "nivel": 7},
)


def test_parsear_mapeo_sobrescribe_y_rechaza_desconocidos():
    capa = parsear_mapeo(["nombre=NOM_DISTRI", "codigo=COD_DIST"], DISTRITOS_DE_PRUEBA)

    # Cambia la propiedad de origen y conserva el conversor del campo.
    assert capa.campos == {"codigo": Origen("COD_DIST", entero), "nombre": Origen("NOM_DISTRI")}
    with pytest.raises(ImportacionError, match="poblacion"):
        parsear_mapeo(["poblacion=POB"], DISTRITOS_DE_PRUEBA)


def test_parsear_mapeo_exige_campo_igual_propiedad():
    with pytest.raises(ImportacionError, match="campo=PROPIEDAD"):
        parsear_mapeo(["nombre"], DISTRITOS_DE_PRUEBA)


def test_mapear_aplica_fijos_y_conserva_atributos_origen():
    propiedades = {"CODIGO": 8461.0, "NOMBRE": " Rocha ", "ALTA": date(2024, 2, 10)}

    assert mapear(Entidad(propiedades, geom=None), CUENCAS_UH7_DE_PRUEBA) == {
        "codigo": "8461",
        "nombre": "Rocha",
        "capa_origen": "uh7",
        "nivel": 7,
        # Valores JSON: las fechas que tipa OGR se guardan en ISO.
        "atributos_origen": {"CODIGO": 8461.0, "NOMBRE": " Rocha ", "ALTA": "2024-02-10"},
    }


def test_mapear_falla_si_falta_propiedad_y_lista_disponibles():
    sin_codigo = Entidad({"NOMBRE": "Rocha", "AREA": 1.5}, geom=None)

    with pytest.raises(
        ImportacionError, match=r"falta la propiedad CODIGO.*disponibles: AREA, NOMBRE"
    ):
        mapear(sin_codigo, CUENCAS_UH7_DE_PRUEBA)


def test_mapear_indica_la_propiedad_que_no_se_puede_convertir():
    codigo_sin_numero = Entidad({"DISTRITO": "DXA", "NOMBRE": "Distrito"}, geom=None)

    with pytest.raises(ImportacionError, match="DISTRITO: no es un número entero: 'DXA'"):
        mapear(codigo_sin_numero, DISTRITOS_DE_PRUEBA)


CAPAS_DEL_PLAN = {
    "distritos",
    "cuencas_uh7",
    "cuencas_uh8",
    "cuencas_influencia",
    "torrenteras",
    "canales",
    "rios",
}


def test_capas_del_plan_estan_declaradas():
    assert set(CAPAS) == CAPAS_DEL_PLAN


def restricciones_unicas(modelo) -> set[tuple[str, ...]]:
    return {
        tuple(sorted(restriccion.fields))
        for restriccion in modelo._meta.constraints
        if isinstance(restriccion, UniqueConstraint) and restriccion.condition is None
    }


CAPAS_IMPORTABLES = {**CAPAS, CAPA_INCIDENTES.nombre: CAPA_INCIDENTES}


@pytest.mark.parametrize("capa", CAPAS_IMPORTABLES.values(), ids=CAPAS_IMPORTABLES.keys())
def test_capas_declaradas_coherentes_con_sus_modelos(capa):
    campos_del_modelo = {campo.name for campo in capa.modelo._meta.get_fields()}

    assert {*capa.claves, *capa.campos, *capa.fijos} <= campos_del_modelo
    # update_or_create solo es idempotente si las claves son una restricción única del modelo.
    assert tuple(sorted(capa.claves)) in restricciones_unicas(capa.modelo)
    assert set(capa.claves) <= {*capa.campos, *capa.fijos}
    assert capa.modelo._meta.get_field("geom").geom_class is capa.tipo_geom


FIXTURES = Path(__file__).parent / "fixtures"


def escribir_geojson(
    ruta: Path, entidades: list[tuple[dict, dict | None]], crs: str | None = None
) -> Path:
    rasgos = [
        {"type": "Feature", "properties": propiedades, "geometry": geometria}
        for propiedades, geometria in entidades
    ]
    coleccion = {"type": "FeatureCollection", "features": rasgos}
    if crs is not None:
        coleccion["crs"] = {"type": "name", "properties": {"name": crs}}
    ruta.write_text(json.dumps(coleccion))
    return ruta


def shapefile_desde(geojson: Path, destino: Path) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ogr2ogr", "-f", "ESRI Shapefile", str(destino), str(geojson)], check=True)
    return destino


def test_leer_archivo_geojson_e_inexistente():
    entidades = leer_archivo(FIXTURES / "distritos_min.geojson")

    assert [entidad.propiedades for entidad in entidades] == [
        {"DISTRITO": "D1", "NOMBRE": "Distrito sintetico 1"},
        {"DISTRITO": "D2", "NOMBRE": "Distrito sintetico 2"},
    ]
    assert {(entidad.geom.geom_name, entidad.geom.srs.srid) for entidad in entidades} == {
        ("MULTIPOLYGON", 4326)
    }
    with pytest.raises(ImportacionError, match="no se pudo abrir"):
        leer_archivo(FIXTURES / "no_existe.geojson")


PUNTO_GEOJSON = {"type": "Point", "coordinates": [-66.16, -17.39]}


def test_leer_archivo_conserva_fechas_como_texto_y_geometria_nula(tmp_path):
    con_zona = {"FECHA": "2024-02-10T23:30:00-04:00", "HORA": "15:30"}
    geojson = escribir_geojson(tmp_path / "x.geojson", [(con_zona, PUNTO_GEOJSON), ({}, None)])

    entidades = leer_archivo(geojson)

    assert entidades[0].propiedades == con_zona
    assert entidades[1].geom is None


def test_leer_archivo_rechaza_fuente_con_varias_capas(tmp_path):
    geojson = escribir_geojson(tmp_path / "x.geojson", [({"ID": 1}, PUNTO_GEOJSON)])
    directorio = tmp_path / "capas"
    shapefile_desde(geojson, directorio / "uno.shp")
    shapefile_desde(geojson, directorio / "dos.shp")

    with pytest.raises(ImportacionError, match="contiene 2 capas"):
        leer_archivo(directorio)


@pytest.mark.parametrize("valor_previo", [None, "NO"], ids=["sin_definir", "definida"])
def test_leer_archivo_restaura_la_opcion_de_fechas_de_gdal(monkeypatch, valor_previo):
    if valor_previo is None:
        monkeypatch.delenv(OPCION_FECHAS_COMO_TEXTO, raising=False)
    else:
        monkeypatch.setenv(OPCION_FECHAS_COMO_TEXTO, valor_previo)

    leer_archivo(FIXTURES / "distritos_min.geojson")

    assert os.environ.get(OPCION_FECHAS_COMO_TEXTO) == valor_previo


EN_UTM_19S = [801768.7727066388, 8075063.815507382]
PROPIEDADES_DE_INCIDENTE = {"ID": "E-1", "FECHA": "2024-02-10", "TIPO": "Inundación"}


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("coordenadas", "crs"),
    [
        pytest.param(EN_UTM_19S, None, id="sin-crs"),
        pytest.param([*EN_UTM_19S, 2550.0], None, id="sin-crs-con-altura"),
        pytest.param(EN_UTM_19S, "EPSG:4326", id="crs-heredado-epsg-4326"),
        pytest.param(EN_UTM_19S, "urn:ogc:def:crs:OGC:1.3:CRS84", id="crs-heredado-crs84"),
    ],
)
def test_geojson_en_wgs84_implicito_admite_srid_indicado(tmp_path, coordenadas, crs):
    # RFC 7946 fija WGS 84 en todo GeoJSON y GDAL no distingue un «crs» heredado que lo repite de
    # uno omitido (con altura, EPSG:4979): con --srid manda el indicado.
    en_utm = {"type": "Point", "coordinates": coordenadas}
    entidades = [(PROPIEDADES_DE_INCIDENTE, en_utm)]
    geojson = escribir_geojson(tmp_path / "utm.geojson", entidades, crs=crs)

    Importacion(CAPA_INCIDENTES, fuente="archivo:utm.geojson", srid_indicado=32719).importar(
        leer_archivo(geojson)
    )

    assert Incidente.objects.get().geom.coords == pytest.approx(PUNTO_EN_CERCADO, abs=1e-6)


# PSAD56 / UTM 19S: un --srid verosímil en Cochabamba que contradice las declaraciones de abajo.
SRID_CONTRADICTORIO = 24879
CRS_UTM_19S = {"type": "name", "properties": {"name": "EPSG:32719"}}


def geojson_con_crs_en_la_coleccion(directorio: Path) -> Path:
    punto = {"type": "Point", "coordinates": EN_UTM_19S}
    entidades = [(PROPIEDADES_DE_INCIDENTE, punto)]
    return escribir_geojson(directorio / "utm.geojson", entidades, crs="EPSG:32719")


def geojson_con_crs_en_la_geometria(directorio: Path) -> Path:
    # GeoJSON 2008 admitía un «crs» por geometría y GDAL lo respeta aunque la colección no tenga.
    punto = {"type": "Point", "coordinates": EN_UTM_19S, "crs": CRS_UTM_19S}
    return escribir_geojson(directorio / "utm.geojson", [(PROPIEDADES_DE_INCIDENTE, punto)])


def shapefile_con_prj_en_wgs84(directorio: Path) -> Path:
    # Un .prj en EPSG:4326 es una declaración: solo el WGS 84 de GeoJSON es implícito.
    punto = {"type": "Point", "coordinates": EN_UTM_19S}
    geojson = escribir_geojson(directorio / "utm.geojson", [(PROPIEDADES_DE_INCIDENTE, punto)])
    return shapefile_desde(geojson, directorio / "shp" / "utm.shp")


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("fuente_de", "declarado"),
    [
        pytest.param(geojson_con_crs_en_la_coleccion, 32719, id="geojson-crs-en-la-coleccion"),
        pytest.param(geojson_con_crs_en_la_geometria, 32719, id="geojson-crs-en-la-geometria"),
        pytest.param(shapefile_con_prj_en_wgs84, 4326, id="shapefile-prj-en-wgs84"),
    ],
)
def test_srs_declarado_no_implicito_rechaza_srid_contradictorio(tmp_path, fuente_de, declarado):
    entidades = leer_archivo(fuente_de(tmp_path))
    importacion = Importacion(
        CAPA_INCIDENTES, fuente="archivo:utm", srid_indicado=SRID_CONTRADICTORIO
    )

    contradiccion = f"--srid {SRID_CONTRADICTORIO} contradice el sistema declarado EPSG:{declarado}"
    with pytest.raises(ImportacionError, match=contradiccion):
        importacion.importar(entidades)

    assert not Incidente.objects.exists()


DISTRITOS_DE_EJEMPLO = FIXTURES / "distritos_min.geojson"
FUENTE_DE_EJEMPLO = "archivo:distritos_min.geojson"


def importar_distritos(entidades: list[Entidad], esperados: int | None = None) -> Resumen:
    importacion = Importacion(CAPAS["distritos"], fuente=FUENTE_DE_EJEMPLO, esperados=esperados)
    return importacion.importar(entidades)


def distritos_guardados() -> list[tuple]:
    return list(Distrito.objects.order_by("codigo").values_list("codigo", "nombre", "fuente_capa"))


@pytest.mark.django_db
def test_importar_crea_registros_con_fuente():
    resumen = importar_distritos(leer_archivo(DISTRITOS_DE_EJEMPLO))

    assert (resumen.creados, resumen.actualizados, resumen.reparadas) == (2, 0, 0)
    assert distritos_guardados() == [
        (1, "Distrito sintetico 1", FUENTE_DE_EJEMPLO),
        (2, "Distrito sintetico 2", FUENTE_DE_EJEMPLO),
    ]


def partes_de_geometria_guardadas() -> int:
    partes = Distrito.objects.annotate(partes=NumGeometries("geom")).aggregate(Sum("partes"))
    return partes["partes__sum"]


@pytest.mark.django_db
def test_reimportar_no_duplica_registros_ni_partes_de_geometria():
    importar_distritos(leer_archivo(DISTRITOS_DE_EJEMPLO))
    resumen = importar_distritos(leer_archivo(DISTRITOS_DE_EJEMPLO))

    assert (resumen.creados, resumen.actualizados) == (0, 2)
    assert (Distrito.objects.count(), partes_de_geometria_guardadas()) == (2, 2)


@pytest.mark.django_db
def test_reimportar_actualiza_atributos():
    primera = importar_distritos(leer_archivo(DISTRITOS_DE_EJEMPLO))
    renombradas = [
        Entidad({**entidad.propiedades, "NOMBRE": f"Nuevo {posicion}"}, entidad.geom)
        for posicion, entidad in enumerate(leer_archivo(DISTRITOS_DE_EJEMPLO), start=1)
    ]
    segunda = importar_distritos(renombradas)

    assert [nombre for _, nombre, _ in distritos_guardados()] == ["Nuevo 1", "Nuevo 2"]
    assert set(Distrito.objects.values_list("cargado_en", flat=True)) == {segunda.cargado_en}
    assert segunda.cargado_en > primera.cargado_en


@pytest.mark.django_db
def test_claves_repetidas_abortan_sin_escribir():
    entidades = leer_archivo(DISTRITOS_DE_EJEMPLO)

    with pytest.raises(ImportacionError, match=r"clave repetida \(1,\)"):
        importar_distritos([*entidades, entidades[0]])
    assert Distrito.objects.count() == 0


@pytest.mark.django_db
def test_importacion_todo_o_nada_lista_todos_los_errores():
    valida, otra = leer_archivo(DISTRITOS_DE_EJEMPLO)
    entidades = [
        valida,
        Entidad({"DISTRITO": "D0", "NOMBRE": "Codigo cero"}, otra.geom),
        Entidad({"DISTRITO": "D5", "NOMBRE": "x" * 101}, otra.geom),
        Entidad({"DISTRITO": "D6", "NOMBRE": "Sin forma"}, geom=None),
    ]

    with pytest.raises(ImportacionError) as error:
        importar_distritos(entidades)

    mensaje = str(error.value)
    assert re.search(r"entidad 2: .*territorio_distrito_codigo_positivo", mensaje)
    assert re.search(r"entidad 3: nombre: .*100 caracteres", mensaje)
    assert re.search(r"entidad 4: entidad sin geometría", mensaje)
    assert "entidad 1" not in mensaje
    assert Distrito.objects.count() == 0


@pytest.mark.django_db
def test_esperados_distinto_aborta_sin_escribir():
    with pytest.raises(ImportacionError, match="se esperaban 15 entidades y la fuente tiene 2"):
        importar_distritos(leer_archivo(DISTRITOS_DE_EJEMPLO), esperados=15)
    assert Distrito.objects.count() == 0


@pytest.mark.django_db
def test_esperados_cuenta_todas_las_entidades_de_la_fuente():
    valida, otra = leer_archivo(DISTRITOS_DE_EJEMPLO)
    sin_forma = Entidad({"DISTRITO": "D6", "NOMBRE": "Sin forma"}, geom=None)

    with pytest.raises(ImportacionError) as error:
        importar_distritos([valida, otra, sin_forma], esperados=3)

    assert "se esperaban" not in str(error.value)


@pytest.mark.django_db
def test_un_fallo_al_escribir_no_deja_registros_a_medias(monkeypatch):
    guardar = Distrito.objects.update_or_create
    guardados = []

    def falla_en_el_segundo(**campos):
        guardados.append(campos)
        if len(guardados) == 2:
            raise DatabaseError("fallo simulado al escribir el segundo distrito")
        return guardar(**campos)

    monkeypatch.setattr(Distrito.objects, "update_or_create", falla_en_el_segundo)

    with pytest.raises(DatabaseError):
        importar_distritos(leer_archivo(DISTRITOS_DE_EJEMPLO))
    assert Distrito.objects.count() == 0


# Dos distritos contiguos (borde común en -66.15), una uh7 que los cubre y una uh8 por distrito.
CAJA_DISTRITO_1 = (-66.17, -17.40, -66.15, -17.38)
CAJA_DISTRITO_2 = (-66.15, -17.40, -66.13, -17.38)
CAJA_CUENCA_UH7 = (-66.20, -17.42, -66.10, -17.36)


def superficie(caja) -> MultiPolygon:
    return MultiPolygon(Polygon.from_bbox(caja), srid=4326)


@pytest.fixture
def territorio_anidado():
    for codigo, caja in ((1, CAJA_DISTRITO_1), (2, CAJA_DISTRITO_2)):
        Distrito.objects.create(
            codigo=codigo, nombre=f"D{codigo}", fuente_capa="prueba", geom=superficie(caja)
        )
    cuencas = (("uh7", "846", CAJA_CUENCA_UH7), ("uh8", "8461", CAJA_DISTRITO_1))
    cuencas += (("uh8", "8462", CAJA_DISTRITO_2),)
    for capa_origen, codigo, caja in cuencas:
        Cuenca.objects.create(
            capa_origen=capa_origen, codigo=codigo, fuente_capa="prueba", geom=superficie(caja)
        )


def codigos(registros) -> list:
    return [registro.codigo if registro else None for registro in registros]


PUNTO_Y_DISTRITO_Y_CUENCA = {
    "interior_del_distrito_1": ((-66.16, -17.39), 1, "8461"),
    "borde_comun": ((-66.15, -17.39), 1, "8461"),
    "solo_en_la_uh7": ((-66.11, -17.39), None, "846"),
    "fuera_de_todo": ((-66.05, -17.39), None, None),
}


@pytest.mark.django_db
@pytest.mark.usefixtures("territorio_anidado")
@pytest.mark.parametrize(
    "caso", PUNTO_Y_DISTRITO_Y_CUENCA.values(), ids=PUNTO_Y_DISTRITO_Y_CUENCA.keys()
)
def test_distrito_y_cuenca_que_contienen_un_punto(caso):
    coordenadas, distrito, cuenca = caso
    punto = Point(*coordenadas, srid=4326)

    # Regla provisional entre cuencas anidadas (README): la de menor área.
    assert codigos([distrito_que_contiene(punto), cuenca_que_contiene(punto)]) == [
        distrito,
        cuenca,
    ]


LINEA_Y_CUENCA = {
    "dentro_de_una_uh8": ((-66.169, -17.39, -66.152, -17.39), "8461"),
    # Cruza dos uh8: la uh7 que las contiene a ambas recoge toda la longitud del cauce.
    "cruza_dos_uh8": ((-66.156, -17.39, -66.136, -17.39), "846"),
    "solo_toca_el_borde_de_la_uh7": ((-66.10, -17.39, -66.08, -17.39), None),
}


@pytest.mark.django_db
@pytest.mark.usefixtures("territorio_anidado")
@pytest.mark.parametrize("caso", LINEA_Y_CUENCA.values(), ids=LINEA_Y_CUENCA.keys())
def test_cuenca_de_mayor_interseccion_de_una_linea(caso):
    (x0, y0, x1, y1), cuenca = caso
    linea = MultiLineString(LineString((x0, y0), (x1, y1)), srid=4326)

    # Igual longitud en la uh7 y en su uh8: decide la de menor área (regla provisional, README).
    assert codigos([cuenca_de_mayor_interseccion(linea)]) == [cuenca]
