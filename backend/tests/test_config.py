import socket

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.db import OperationalError
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from config.entorno import env_bool, env_lista, env_requerida

VARIABLE = "SAT_VARIABLE_DE_PRUEBA"
AUSENTE = None


def definir_variable(monkeypatch, valor):
    if valor is AUSENTE:
        monkeypatch.delenv(VARIABLE, raising=False)
    else:
        monkeypatch.setenv(VARIABLE, valor)


@pytest.mark.parametrize("valor", [AUSENTE, "", "   "], ids=["ausente", "vacia", "espacios"])
def test_env_requerida_falla_si_falta_o_esta_vacia(monkeypatch, valor):
    definir_variable(monkeypatch, valor)

    with pytest.raises(ImproperlyConfigured, match=VARIABLE):
        env_requerida(VARIABLE)


def test_env_requerida_devuelve_el_valor(monkeypatch):
    definir_variable(monkeypatch, "  sat_cochabamba  ")

    assert env_requerida(VARIABLE) == "sat_cochabamba"


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [("true", True), ("True", True), ("1", True), ("si", True), ("false", False), ("0", False)],
)
def test_env_bool_acepta_verdaderos_y_es_falso_por_defecto(monkeypatch, valor, esperado):
    definir_variable(monkeypatch, valor)
    leido = env_bool(VARIABLE)
    definir_variable(monkeypatch, AUSENTE)

    assert (leido, env_bool(VARIABLE)) == (esperado, False)


def test_env_bool_rechaza_valor_no_reconocido(monkeypatch):
    definir_variable(monkeypatch, "quizas")

    with pytest.raises(ImproperlyConfigured, match=VARIABLE):
        env_bool(VARIABLE)


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (AUSENTE, []),
        ("", []),
        ("localhost", ["localhost"]),
        (" localhost, 127.0.0.1 ,,", ["localhost", "127.0.0.1"]),
    ],
)
def test_env_lista_separa_por_comas_y_descarta_vacios(monkeypatch, valor, esperado):
    definir_variable(monkeypatch, valor)

    assert env_lista(VARIABLE) == esperado


@pytest.mark.django_db
def test_healthz_responde_200_con_bd_disponible(client):
    respuesta = client.get("/healthz/")

    assert (respuesta.status_code, respuesta.json()) == (200, {"estado": "ok"})


class ConexionCaida:
    def ensure_connection(self):
        raise OperationalError("could not connect to server: host db, puerto 5432")


def test_healthz_responde_503_sin_detalle_si_la_bd_falla(client, monkeypatch):
    monkeypatch.setattr("config.salud.connection", ConexionCaida())

    respuesta = client.get("/healthz/")

    assert (respuesta.status_code, respuesta.json()) == (503, {"estado": "no_disponible"})


def test_cors_solo_autoriza_origenes_configurados(client, settings):
    settings.CORS_ALLOWED_ORIGINS = ["https://visor.example"]

    permitida = client.get("/api/v1/", headers={"origin": "https://visor.example"})
    ajena = client.get("/api/v1/", headers={"origin": "https://ajena.example"})

    assert permitida.headers.get("access-control-allow-origin") == "https://visor.example"
    assert "access-control-allow-origin" not in ajena.headers


class VistaSinPermisosExplicitos(APIView):
    def get(self, request):
        return Response({})


def test_drf_deniega_por_defecto():
    peticion_anonima = APIRequestFactory().get("/api/v1/privado/")

    respuesta = VistaSinPermisosExplicitos.as_view()(peticion_anonima)

    assert respuesta.status_code == 403


DIRECCION_DE_DOCUMENTACION = ("192.0.2.1", 80)  # TEST-NET-1 (RFC 5737): nunca enrutable


def test_las_pruebas_no_pueden_abrir_conexiones_de_red():
    with pytest.raises(RuntimeError, match="red bloqueada"):
        socket.create_connection(DIRECCION_DE_DOCUMENTACION, timeout=1)
