import socket

import pytest

FAMILIAS_DE_RED = frozenset({socket.AF_INET, socket.AF_INET6})


class RedBloqueadaError(RuntimeError):
    """Una prueba intentó abrir una conexión de red real."""


@pytest.fixture(autouse=True)
def bloquear_red(monkeypatch):
    """Impide conexiones de red reales: las pruebas usan dobles y fixtures locales.

    La base de datos no se ve afectada: psycopg conecta mediante libpq, no con sockets de Python.
    """
    conectar_original = socket.socket.connect

    def conectar_sin_red(conexion, direccion):
        if conexion.family in FAMILIAS_DE_RED:
            raise RedBloqueadaError(f"Conexión de red bloqueada en las pruebas: {direccion!r}")
        return conectar_original(conexion, direccion)

    monkeypatch.setattr(socket.socket, "connect", conectar_sin_red)
