from datetime import UTC, date, datetime, timedelta

import pytest
from django.apps import apps
from django.contrib.gis.geos import LineString, MultiLineString, MultiPolygon, Point, Polygon
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.models import ProtectedError
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from test_arquitectura import DEPENDENCIAS_PERMITIDAS

from clima.models import LLUVIA_MAXIMA_MM, HumedadSuelo, LecturaLluvia
from incidentes.models import Incidente
from radar.models import EscenaSAR
from riesgo.models import Alerta, IndiceRiesgo, NivelAlerta
from territorio.models import Cuenca, Distrito, Torrentera

INICIO = datetime(2024, 2, 10, 12, tzinfo=UTC)
FIN = INICIO + timedelta(hours=1)

CAJA_CERCADO = (-66.17, -17.40, -66.15, -17.38)


def area_de_prueba() -> MultiPolygon:
    return MultiPolygon(Polygon.from_bbox(CAJA_CERCADO), srid=4326)


def crear_distrito(codigo: int) -> Distrito:
    return Distrito.objects.create(
        codigo=codigo, nombre=f"Distrito {codigo}", fuente_capa="prueba", geom=area_de_prueba()
    )


def crear_cuenca(capa_origen: str, codigo: str) -> Cuenca:
    return Cuenca.objects.create(
        capa_origen=capa_origen, codigo=codigo, fuente_capa="prueba", geom=area_de_prueba()
    )


def crear_torrentera(tipo: str, id_origen: str) -> Torrentera:
    cauce = MultiLineString(LineString((-66.165, -17.395), (-66.155, -17.385)), srid=4326)
    return Torrentera.objects.create(
        tipo=tipo, id_origen=id_origen, fuente_capa="prueba", geom=cauce
    )


def crear_incidente(id_origen: str) -> Incidente:
    return Incidente.objects.create(
        id_origen=id_origen,
        fecha=date(2024, 2, 10),
        tipo_evento_origen="Inundación",
        clase="inundacion",
        geom=Point(-66.16, -17.39, srid=4326),
        fuente_capa="prueba",
    )


def lectura_lluvia(**campos) -> LecturaLluvia:
    valores = {"inicio": INICIO, "fin": FIN, "valor_mm": 3.2, "fuente": "imerg_late"}
    valores |= {"version_producto": "V07C", "metodo_agregacion": "media_area"}
    return LecturaLluvia(**valores | {"fraccion_valida": 1.0} | campos)


def humedad_suelo(**campos) -> HumedadSuelo:
    valores = {"inicio": INICIO, "fin": FIN, "valor": 0.31, "unidad_medida": "m3_m3"}
    valores |= {"capa": "superficial", "fuente": "smap_9km", "version_producto": "v9"}
    return HumedadSuelo(**valores | campos)


def indice_riesgo(**campos) -> IndiceRiesgo:
    valores = {"tipo": "amenaza", "fecha_hora_ref": INICIO, "valor": 0.4, "nivel": "amarilla"}
    return IndiceRiesgo(**valores | {"version_metodo": "v0"} | campos)


def nueva_alerta(**campos) -> Alerta:
    valores = {"nivel": "naranja", "amenaza": "inundacion", "origen": "modelo_sat"}
    return Alerta(**valores | {"vigente_desde": INICIO, "vigente_hasta": FIN} | campos)


PRODUCTO_SAR = "S1A_IW_GRDH_1SDV_20240210T100000_PRUEBA"


def escena_sar(polarizacion: str, **campos) -> EscenaSAR:
    valores = {"id_producto": PRODUCTO_SAR, "polarizacion": polarizacion, "proveedor": "cdse"}
    valores |= {"tipo_producto": "GRD", "plataforma": "S1A", "fecha_adquisicion": INICIO}
    valores |= {"paso_orbita": "DESC", "orbita_relativa": 127}
    valores |= {"huella": Polygon.from_bbox(CAJA_CERCADO), "ruta_archivo": "s1/escena.tif"}
    return EscenaSAR(**valores | campos)


def guardada(instancia):
    instancia.save()
    return instancia


def en_distrito(fabrica):
    return lambda: guardada(fabrica(distrito=crear_distrito(1)))


def escena_vv():
    return guardada(escena_sar("VV"))


FUERA_DEL_DOMINIO = {
    "distrito_tipo_area": (lambda: crear_distrito(1), "tipo_area", "selva"),
    "cuenca_capa_origen": (lambda: crear_cuenca("uh7", "8461"), "capa_origen", "uh9"),
    "cuenca_nivel_fuera_del_catalogo": (lambda: crear_cuenca("influencia", "8461"), "nivel", 9),
    "cuenca_nivel_de_otra_capa": (lambda: crear_cuenca("uh7", "8461"), "nivel", 8),
    "torrentera_tipo": (lambda: crear_torrentera("torrentera", "12"), "tipo", "acequia"),
    "incidente_clase": (lambda: crear_incidente("E-001"), "clase", "sismo"),
    "incidente_conjunto": (lambda: crear_incidente("E-001"), "conjunto", "entrenamiento"),
    "lluvia_fuente": (en_distrito(lectura_lluvia), "fuente", "gsmap"),
    "lluvia_metodo": (en_distrito(lectura_lluvia), "metodo_agregacion", "mediana"),
    "humedad_unidad": (en_distrito(humedad_suelo), "unidad_medida", "pct"),
    "humedad_capa": (en_distrito(humedad_suelo), "capa", "profunda"),
    "humedad_fuente": (en_distrito(humedad_suelo), "fuente", "era5_land"),
    "indice_tipo": (en_distrito(indice_riesgo), "tipo", "vulnerabilidad"),
    "indice_nivel": (en_distrito(indice_riesgo), "nivel", "morada"),
    "alerta_nivel": (en_distrito(nueva_alerta), "nivel", "morada"),
    "alerta_amenaza": (en_distrito(nueva_alerta), "amenaza", "sequia"),
    "alerta_origen": (en_distrito(nueva_alerta), "origen", "prensa"),
    "alerta_estado": (en_distrito(nueva_alerta), "estado", "archivada"),
    "escena_polarizacion": (escena_vv, "polarizacion", "HH"),
    "escena_proveedor": (escena_vv, "proveedor", "esa"),
    "escena_paso_orbita": (escena_vv, "paso_orbita", "ASCENDING"),
    "escena_orbita_relativa": (escena_vv, "orbita_relativa", 0),
}

REGISTRO_POR_MODELO = {
    "territorio_distrito": lambda: crear_distrito(1),
    "territorio_cuenca": lambda: crear_cuenca("uh7", "8461"),
    "territorio_torrentera": lambda: crear_torrentera("torrentera", "12"),
    "incidentes_incidente": lambda: crear_incidente("E-001"),
    "clima_lecturalluvia": en_distrito(lectura_lluvia),
    "clima_humedadsuelo": en_distrito(humedad_suelo),
    "radar_escenasar": escena_vv,
    "riesgo_indiceriesgo": en_distrito(indice_riesgo),
    "riesgo_alerta": en_distrito(nueva_alerta),
}

MEDICIONES = [lectura_lluvia, humedad_suelo, indice_riesgo]
NOMBRES_MEDICIONES = ["LecturaLluvia", "HumedadSuelo", "IndiceRiesgo"]
PERIODICAS = MEDICIONES[:2]
NOMBRES_PERIODICAS = NOMBRES_MEDICIONES[:2]

PORCENTAJE = {"unidad_medida": "pct_saturacion"}
LIMITE_Y_FUERA_DE_RANGO = {
    "lluvia_maxima": (
        lectura_lluvia,
        {"valor_mm": LLUVIA_MAXIMA_MM},
        {"valor_mm": LLUVIA_MAXIMA_MM + 0.1},
    ),
    "lluvia_negativa": (lectura_lluvia, {"valor_mm": 0.0}, {"valor_mm": -0.1}),
    "lluvia_nan": (lectura_lluvia, {"valor_mm": 0.0}, {"valor_mm": float("nan")}),
    "fraccion_valida": (lectura_lluvia, {"fraccion_valida": 0.0}, {"fraccion_valida": 1.01}),
    "humedad_m3_m3": (humedad_suelo, {"valor": 1.0}, {"valor": 1.2}),
    "humedad_pct": (humedad_suelo, PORCENTAJE | {"valor": 100.0}, PORCENTAJE | {"valor": 100.5}),
    "indice_infinito": (indice_riesgo, {"valor": 1.0}, {"valor": float("inf")}),
}


@pytest.mark.django_db
def test_distrito_codigo_unico_y_positivo():
    crear_distrito(7)

    with pytest.raises(IntegrityError), transaction.atomic():
        crear_distrito(7)
    with pytest.raises(IntegrityError), transaction.atomic():
        crear_distrito(0)


@pytest.mark.django_db
def test_cuenca_unica_por_capa_y_codigo():
    crear_cuenca("uh7", "8461")
    crear_cuenca("uh8", "8461")

    with pytest.raises(IntegrityError), transaction.atomic():
        crear_cuenca("uh7", "8461")


@pytest.mark.django_db
def test_torrentera_unica_por_tipo_e_id_origen():
    crear_torrentera("torrentera", "12")
    crear_torrentera("canal", "12")

    with pytest.raises(IntegrityError), transaction.atomic():
        crear_torrentera("torrentera", "12")


@pytest.mark.django_db
def test_incidente_id_origen_unico():
    crear_incidente("E-001")

    with pytest.raises(IntegrityError), transaction.atomic():
        crear_incidente("E-001")


@pytest.mark.django_db
@pytest.mark.parametrize("medicion", MEDICIONES, ids=NOMBRES_MEDICIONES)
def test_medicion_exige_exactamente_una_unidad_territorial(medicion):
    distrito, cuenca = crear_distrito(1), crear_cuenca("uh7", "8461")

    with pytest.raises(IntegrityError), transaction.atomic():
        medicion().save()
    with pytest.raises(IntegrityError), transaction.atomic():
        medicion(distrito=distrito, cuenca=cuenca).save()


@pytest.mark.django_db
@pytest.mark.parametrize("medicion", MEDICIONES, ids=NOMBRES_MEDICIONES)
def test_medicion_unica_aunque_la_otra_unidad_sea_nula(medicion):
    distrito, cuenca = crear_distrito(1), crear_cuenca("uh7", "8461")
    medicion(distrito=distrito).save()
    medicion(cuenca=cuenca).save()
    medicion(distrito=crear_distrito(2)).save()

    with pytest.raises(IntegrityError), transaction.atomic():
        medicion(distrito=distrito).save()
    with pytest.raises(IntegrityError), transaction.atomic():
        medicion(cuenca=cuenca).save()


@pytest.mark.django_db
@pytest.mark.parametrize("medicion", PERIODICAS, ids=NOMBRES_PERIODICAS)
def test_periodo_exige_fin_posterior_a_inicio(medicion):
    distrito = crear_distrito(1)

    with pytest.raises(IntegrityError), transaction.atomic():
        medicion(distrito=distrito, fin=INICIO).save()
    with pytest.raises(IntegrityError), transaction.atomic():
        medicion(distrito=distrito, fin=INICIO - timedelta(minutes=30)).save()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "caso", LIMITE_Y_FUERA_DE_RANGO.values(), ids=LIMITE_Y_FUERA_DE_RANGO.keys()
)
def test_valores_fuera_de_rango_se_rechazan(caso):
    medicion, en_limite, fuera_de_rango = caso
    medicion(distrito=crear_distrito(1), **en_limite).save()

    with pytest.raises(IntegrityError), transaction.atomic():
        medicion(distrito=crear_distrito(2), **fuera_de_rango).save()


@pytest.mark.django_db
def test_escena_sar_unica_por_producto_y_polarizacion():
    escena_sar("VV").save()
    escena_sar("VH").save()

    with pytest.raises(IntegrityError), transaction.atomic():
        escena_sar("VV").save()


RUTAS_FUERA_DEL_DIRECTORIO_DE_DATOS = [
    "/datos/s1/escena.tif",
    "C:/datos/escena.tif",
    "C:\\datos\\escena.tif",
    "C:escena.tif",
    "\\\\servidor\\compartido\\escena.tif",
    "s1/../../etc/passwd",
    "..\\escena.tif",
]


@pytest.mark.django_db
@pytest.mark.parametrize("ruta", RUTAS_FUERA_DEL_DIRECTORIO_DE_DATOS)
def test_ruta_archivo_rechaza_absoluta_y_salto_de_directorio(ruta):
    escena_sar("VV", ruta_archivo="s1/2024/escena_vv.tif").full_clean()

    with pytest.raises(ValidationError) as error:
        escena_sar("VV", ruta_archivo=ruta).full_clean()
    assert "ruta_archivo" in error.value.message_dict


@pytest.mark.django_db
def test_alerta_nace_propuesta_con_vigencia_coherente():
    distrito = crear_distrito(1)
    alerta = nueva_alerta(distrito=distrito)
    alerta.save()

    assert (alerta.estado, alerta.emitida_en) == ("propuesta", None)
    with pytest.raises(IntegrityError), transaction.atomic():
        nueva_alerta(distrito=distrito, vigente_hasta=INICIO).save()


@pytest.mark.django_db
def test_alerta_emitida_exige_emitida_en():
    distrito = crear_distrito(1)
    nueva_alerta(distrito=distrito, estado="emitida", emitida_en=INICIO).save()

    with pytest.raises(IntegrityError), transaction.atomic():
        nueva_alerta(distrito=distrito, estado="emitida").save()


@pytest.mark.django_db
def test_alerta_reemplaza_a_otra():
    distrito = crear_distrito(1)
    original = nueva_alerta(distrito=distrito)
    original.save()
    sustituta = nueva_alerta(distrito=distrito, nivel="roja", reemplaza=original)
    sustituta.save()

    assert list(original.reemplazada_por.all()) == [sustituta]
    with pytest.raises(ProtectedError):
        original.delete()
    with pytest.raises(IntegrityError), transaction.atomic():
        Alerta.objects.filter(pk=sustituta.pk).update(reemplaza=sustituta)


def test_nivel_alerta_compartido_por_indice_y_alerta():
    niveles = [modelo._meta.get_field("nivel").choices for modelo in (IndiceRiesgo, Alerta)]

    assert niveles == [NivelAlerta.choices, NivelAlerta.choices]


@pytest.mark.django_db
@pytest.mark.parametrize("modelo", REGISTRO_POR_MODELO.keys())
def test_admin_lista_y_alta_responden_200(admin_client, modelo):
    REGISTRO_POR_MODELO[modelo]()

    estados = [
        admin_client.get(reverse(f"admin:{modelo}_{vista}")).status_code
        for vista in ("changelist", "add")
    ]
    assert estados == [200, 200]


@pytest.mark.django_db
@pytest.mark.parametrize("modelo", REGISTRO_POR_MODELO.keys())
def test_cada_registro_tiene_una_representacion_legible(modelo):
    registro = REGISTRO_POR_MODELO[modelo]()

    assert "object (" not in str(registro)


def relaciones_prohibidas() -> dict[str, list[str]]:
    """FK de cada modelo hacia apps que no puede conocer; usa el mismo mapa que los imports."""
    infracciones = {}
    for modelo in apps.get_models():
        origen = modelo._meta.app_label
        if origen not in DEPENDENCIAS_PERMITIDAS:
            continue
        destinos = {
            campo.related_model._meta.app_label
            for campo in modelo._meta.get_fields()
            if campo.is_relation and campo.concrete
        }
        if prohibidos := destinos - DEPENDENCIAS_PERMITIDAS[origen] - {origen}:
            infracciones[modelo._meta.label] = sorted(prohibidos)
    return infracciones


def test_relaciones_entre_modelos_respetan_el_sentido_permitido():
    assert relaciones_prohibidas() == {}


# PostgreSQL trunca en silencio los identificadores de más de 63 bytes (NAMEDATALEN - 1).
LIMITE_IDENTIFICADOR_POSTGRESQL = 63


def test_nombres_de_restricciones_caben_en_postgresql():
    nombres = (r.name for m in apps.get_models() for r in m._meta.constraints)

    assert [n for n in nombres if len(n.encode()) > LIMITE_IDENTIFICADOR_POSTGRESQL] == []


@pytest.mark.django_db
@pytest.mark.parametrize("caso", FUERA_DEL_DOMINIO.values(), ids=FUERA_DEL_DOMINIO.keys())
def test_valores_fuera_del_dominio_se_rechazan(caso):
    """choices solo valida formularios; un UPDATE directo debe chocar con un CHECK de la base."""
    fabrica, campo, valor = caso
    registro = fabrica()

    with pytest.raises(IntegrityError), transaction.atomic():
        type(registro).objects.filter(pk=registro.pk).update(**{campo: valor})


NIVELES_COHERENTES_CON_SU_CAPA = [("uh7", 7), ("uh8", 8), ("influencia", 8), ("uh7", None)]


@pytest.mark.django_db
@pytest.mark.parametrize("capa_y_nivel", NIVELES_COHERENTES_CON_SU_CAPA, ids=str)
def test_cuenca_acepta_el_nivel_de_su_capa(capa_y_nivel):
    capa, nivel = capa_y_nivel
    cuenca = crear_cuenca(capa, "8461")

    Cuenca.objects.filter(pk=cuenca.pk).update(nivel=nivel)
    assert Cuenca.objects.get(pk=cuenca.pk).nivel == nivel


@pytest.mark.django_db
def test_editar_un_registro_importado_conserva_cargado_en():
    distrito = crear_distrito(1)
    cargado_en = distrito.cargado_en

    distrito.nombre = "Distrito renombrado a mano"
    distrito.save()
    distrito.refresh_from_db()
    assert distrito.cargado_en == cargado_en


def en_unidad_alterna(fabrica):
    """Filas impares en un distrito y pares en una cuenca, para ejercitar las dos FK."""

    def crear(numero):
        if numero % 2:
            return guardada(fabrica(distrito=crear_distrito(numero)))
        return guardada(fabrica(cuenca=crear_cuenca("uh7", str(numero))))

    return crear


def incidente_en_distrito(numero):
    incidente = crear_incidente(f"E-{numero:03d}")
    incidente.distrito = crear_distrito(numero)
    return guardada(incidente)


def torrentera_en_cuenca(numero):
    torrentera = crear_torrentera("torrentera", str(numero))
    torrentera.cuenca = crear_cuenca("uh7", str(numero))
    return guardada(torrentera)


# Listados del admin con una FK anulable en list_display: select_related() sin argumentos no
# la sigue.
FILA_CON_UNIDAD_POR_MODELO = {
    "clima_lecturalluvia": en_unidad_alterna(lectura_lluvia),
    "clima_humedadsuelo": en_unidad_alterna(humedad_suelo),
    "riesgo_indiceriesgo": en_unidad_alterna(indice_riesgo),
    "incidentes_incidente": incidente_en_distrito,
    "territorio_torrentera": torrentera_en_cuenca,
}


def consultas_del_listado(admin_client, modelo) -> int:
    with CaptureQueriesContext(connection) as consultas:
        admin_client.get(reverse(f"admin:{modelo}_changelist"))
    return len(consultas)


@pytest.mark.django_db
@pytest.mark.parametrize("modelo", FILA_CON_UNIDAD_POR_MODELO.keys())
def test_listado_del_admin_no_consulta_por_fila(admin_client, modelo):
    crear_fila = FILA_CON_UNIDAD_POR_MODELO[modelo]
    crear_fila(1)
    con_una_fila = consultas_del_listado(admin_client, modelo)
    crear_fila(2)
    crear_fila(3)

    assert consultas_del_listado(admin_client, modelo) == con_una_fila


# Un JSON vacío en el formulario llega como None a una columna NOT NULL: error 500 al guardar.
CAMPO_JSON_POR_MODELO = {
    "territorio_distrito": "atributos_origen",
    "territorio_cuenca": "atributos_origen",
    "territorio_torrentera": "atributos_origen",
    "incidentes_incidente": "atributos_origen",
    "riesgo_indiceriesgo": "componentes",
}


@pytest.mark.django_db
@pytest.mark.parametrize("caso", CAMPO_JSON_POR_MODELO.items(), ids=CAMPO_JSON_POR_MODELO.keys())
def test_admin_muestra_los_campos_json_como_solo_lectura(admin_client, caso):
    modelo, campo = caso
    respuesta = admin_client.get(reverse(f"admin:{modelo}_add"))

    assert campo in respuesta.context["adminform"].readonly_fields
