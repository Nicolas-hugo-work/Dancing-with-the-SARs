"""Lectura de variables de entorno que falla cerrada ante configuración ausente o inválida."""

import os

from django.core.exceptions import ImproperlyConfigured

VERDADEROS = frozenset({"1", "true", "si", "yes", "on"})
FALSOS = frozenset({"", "0", "false", "no", "off"})


def env_requerida(nombre: str) -> str:
    """Devuelve el valor de la variable; lanza ImproperlyConfigured si falta o está vacía."""
    valor = os.environ.get(nombre, "").strip()
    if not valor:
        raise ImproperlyConfigured(f"Falta la variable de entorno {nombre} o está vacía.")
    return valor


def env_bool(nombre: str) -> bool:
    """Interpreta la variable como booleano; ausente o vacía equivale a falso."""
    valor = os.environ.get(nombre, "").strip().lower()
    if valor in VERDADEROS:
        return True
    if valor in FALSOS:
        return False
    raise ImproperlyConfigured(f"La variable {nombre} debe ser verdadera o falsa (true/false).")


def env_lista(nombre: str) -> list[str]:
    """Separa la variable por comas, sin espacios ni elementos vacíos; ausente equivale a []."""
    partes = (parte.strip() for parte in os.environ.get(nombre, "").split(","))
    return [parte for parte in partes if parte]
