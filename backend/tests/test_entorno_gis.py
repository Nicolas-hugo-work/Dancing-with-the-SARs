from pathlib import Path

from django.contrib.gis.gdal import DataSource, gdal_version
from django.contrib.gis.geos import GEOSGeometry, geos_version

# Rangos de la tabla «Geospatial libraries» de la documentación de Django 5.2.
GDAL_SOPORTADO = ((3, 1), (3, 10))
GEOS_SOPORTADO = ((3, 8), (3, 13))

RUTA_DISTRITOS = Path(__file__).parent / "fixtures" / "distritos_min.geojson"
DISTRITOS_EN_FIXTURE = 2
UTM_19S = 32719


def mayor_y_menor(version: bytes) -> tuple[int, int]:
    mayor, menor = version.decode().split(".")[:2]
    return int(mayor), int(menor)


def en_rango(version: tuple[int, int], rango: tuple[tuple[int, int], tuple[int, int]]) -> bool:
    minima, maxima = rango
    return minima <= version <= maxima


def test_gdal_y_geos_del_sistema_en_rango_de_django_52():
    gdal = mayor_y_menor(gdal_version())
    geos = mayor_y_menor(geos_version())

    assert (en_rango(gdal, GDAL_SOPORTADO), en_rango(geos, GEOS_SOPORTADO)) == (True, True)


def proyectar_punto_de_cercado() -> tuple[float, float]:
    punto = GEOSGeometry("POINT (-66.157 -17.3895)", srid=4326)
    punto.transform(UTM_19S)
    return round(punto.x, 2), round(punto.y, 2)


def usar_gdal_embebido() -> tuple[str, int]:
    """Ejercita el GDAL de las wheels: rasterio escribe un raster y pyogrio lee la fixture."""
    import geopandas
    import numpy
    import rasterio
    from rasterio.transform import from_origin

    georreferencia = {"crs": "EPSG:4326", "transform": from_origin(-66.17, -17.38, 0.01, 0.01)}
    with rasterio.MemoryFile() as memoria:
        opciones = {"driver": "GTiff", "width": 1, "height": 1, "count": 1, "dtype": "uint8"}
        with memoria.open(**opciones, **georreferencia) as raster:
            raster.write(numpy.zeros((1, 1, 1), dtype="uint8"))
    return rasterio.__gdal_version__, len(geopandas.read_file(RUTA_DISTRITOS))


def test_dos_gdal_conviven_en_el_mismo_proceso(record_property):
    proyectado_antes = proyectar_punto_de_cercado()

    gdal_embebido, leidos_por_pyogrio = usar_gdal_embebido()
    record_property("gdal_rasterio", gdal_embebido)
    leidos_por_geodjango = len(DataSource(str(RUTA_DISTRITOS))[0])

    assert proyectar_punto_de_cercado() == proyectado_antes
    assert (leidos_por_pyogrio, leidos_por_geodjango) == (DISTRITOS_EN_FIXTURE,) * 2
