import ast
from collections.abc import Iterator
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
APPS = ("territorio", "incidentes", "clima", "radar", "riesgo")
DEPENDENCIAS_PERMITIDAS = {
    "territorio": frozenset(),
    "incidentes": frozenset({"territorio"}),
    "clima": frozenset({"territorio"}),
    "radar": frozenset({"territorio"}),
    "riesgo": frozenset({"territorio", "incidentes", "clima", "radar"}),
}
# Ninguna app puede importar config: la configuración depende de las apps, no al revés.
MODULOS_DEL_PROYECTO = frozenset(APPS) | {"config"}


def arbol_de(ruta: Path) -> ast.Module:
    return ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))


def nombres_definidos(arbol: ast.AST) -> Iterator[str]:
    for nodo in ast.walk(arbol):
        match nodo:
            case ast.FunctionDef(name=nombre) | ast.AsyncFunctionDef(name=nombre):
                yield nombre
            case ast.ClassDef(name=nombre) | ast.arg(arg=nombre):
                yield nombre
            case ast.Name(id=nombre, ctx=ast.Store()) | ast.Attribute(attr=nombre, ctx=ast.Store()):
                yield nombre
            case ast.alias(asname=str() as nombre):
                yield nombre


def identificadores_no_ascii(raiz: Path) -> dict[str, list[str]]:
    """Devuelve, por archivo, los nombres de módulo y los identificadores definidos no ASCII."""
    infracciones = {}
    for ruta in sorted(raiz.rglob("*.py")):
        relativa = ruta.relative_to(raiz)
        nombres = [*relativa.with_suffix("").parts, *nombres_definidos(arbol_de(ruta))]
        if no_ascii := [nombre for nombre in nombres if not nombre.isascii()]:
            infracciones[str(relativa)] = no_ascii
    return infracciones


def modulos_importados(arbol: ast.AST) -> set[str]:
    importados = set()
    for nodo in ast.walk(arbol):
        match nodo:
            case ast.Import(names=alias):
                importados |= {nombre.name.split(".")[0] for nombre in alias}
            case ast.ImportFrom(module=str() as modulo, level=0):
                importados.add(modulo.split(".")[0])
    return importados


def modulos_importados_por(directorio: Path) -> set[str]:
    return set().union(*(modulos_importados(arbol_de(ruta)) for ruta in directorio.rglob("*.py")))


def imports_prohibidos(raiz: Path) -> dict[str, list[str]]:
    """Devuelve, por app, los módulos del proyecto que importa fuera del sentido permitido."""
    infracciones = {}
    for app in APPS:
        importados = modulos_importados_por(raiz / app)
        permitidos = DEPENDENCIAS_PERMITIDAS[app] | {app}
        if prohibidos := (importados & MODULOS_DEL_PROYECTO) - permitidos:
            infracciones[app] = sorted(prohibidos)
    return infracciones


def test_identificadores_python_son_ascii():
    assert identificadores_no_ascii(RAIZ) == {}


def test_imports_entre_apps_respetan_el_sentido_permitido():
    assert imports_prohibidos(RAIZ) == {}
