# Dancing with the SARs — Alerta Temprana de Riesgos en Cuencas (Cochabamba)

Sistema de Alerta Temprana (SAT) de **inundaciones** y **mapa de riesgo por distrito** para el municipio de
Cochabamba (Cercado), Bolivia. Reto del Gobierno Autónomo Municipal de Cochabamba (GAMC).

La amenaza se evalúa por cuenca o torrentera (lluvia satelital, humedad antecedente y confirmación con radar
Sentinel-1) y el riesgo se agrega a cada distrito por intersección espacial. El sistema **propone** alertas con los
niveles de la Ley 602 (verde, amarilla, naranja, roja); la declaratoria corresponde a la autoridad competente (art. 38).

## Stack

| Capa | Herramienta |
| --- | --- |
| Framework | Django 5.2 LTS + GeoDjango |
| API | Django REST Framework + djangorestframework-gis |
| Documentación | drf-spectacular (OpenAPI 3, Swagger UI) |
| Base de datos | PostgreSQL 17 + PostGIS 3.7 |
| Procesamiento | rasterio, xarray, geopandas, numpy (solo en management commands) |
| Infraestructura | Docker Compose |
| Utilidades | django-cors-headers, python-dotenv |

## Estructura

```text
backend/
├── config/       # settings, urls, healthcheck
├── territorio/   # Distrito, Cuenca, Torrentera; importadores (archivo y WMS del GAMC)
├── incidentes/   # Incidente (casos de validación de la capa «Emergencias» del GAMC)
├── clima/        # LecturaLluvia, HumedadSuelo (fuentes satelitales)
├── riesgo/       # IndiceRiesgo, Alerta
├── radar/        # EscenaSAR (Sentinel-1)
└── tests/
```

Dependencias entre apps en un solo sentido: `territorio` ← `incidentes` | `clima` | `radar` ← `riesgo`.
Ninguna app base importa `riesgo`, y ninguna app importa `config`. Las pruebas de arquitectura lo verifican.

## Convenciones del proyecto

- **Identificadores en español, solo ASCII**: `polarizacion`, `anio`, `orbita_relativa` (sin tildes ni ñ en nombres
  de módulos, clases, funciones, campos ni rutas). Es una regla del proyecto y la comprueba una prueba.
- **Tiempo**: se guarda en UTC (`USE_TZ=True`); la zona de presentación es `America/La_Paz`.
- **Geometrías**: SRID 4326 (WGS84). Las áreas y longitudes se calculan en EPSG:32719 (UTM 19S).
- **Secretos**: solo en `.env` local (ver `.env.example`). La clave del WMS del GAMC nunca se escribe en código,
  pruebas, fixtures, issues ni capturas.
- **Datos reales**: en `backend/datos/`, que no se versiona.
- **Calidad**: desarrollo guiado por pruebas (pytest + pytest-django) y `ruff` como formateador y linter.

## Decisiones de esquema

Revisadas con un especialista en bases de datos (PostgreSQL 17 + PostGIS 3.7, Django 5.2) antes de la primera
migración. Las migraciones se revisan con `sqlmigrate` antes de cada commit.

| Tema | Decisión |
| --- | --- |
| Unidad territorial de las mediciones | Dos FK nulas (`cuenca`, `distrito`) y un `CHECK` «exactamente una» |
| Unicidad de las series | Dos índices únicos parciales por tabla (uno por FK, con la unidad como primera columna) |
| Claves naturales | Lluvia: unidad, fuente, método, inicio, fin, versión; humedad: unidad, fuente, capa, inicio, fin, versión; índice: unidad, tipo, fecha de referencia, versión del método |
| Magnitudes | `FloatField` con `CHECK ... BETWEEN` (rechaza `NaN` e infinito); los cálculos acotan antes de guardar |
| Borrado | `PROTECT` en todas las FK, incluida `Alerta.reemplaza`: las alertas se cancelan, no se borran |
| Choices cerradas | Reforzadas con `CHECK ... IN`; no en catálogos cambiantes (`subalcaldia`) ni en textos de la fuente |
| Índices | Solo los únicos, los de FK y los GiST de cada geometría; sin índices adicionales hasta medir |
| Rol de base de datos | En desarrollo, el usuario de la imagen PostGIS (superusuario) y `TEST.TEMPLATE = template_postgis`; en producción, rol de migración distinto del rol de la aplicación, sin `CREATEDB` |

Pendientes de dominio, a confirmar con datos reales: regla de desempate entre capas de cuencas anidadas, zona
horaria de la fecha y hora de los incidentes de origen, metadatos de escenas SAR por polarización y método de
agregación de la humedad del suelo.

## Flujo Git

- `develop` es la rama de trabajo y la rama predeterminada del repositorio. No se usa `main`.
- Los cambios se integran en `develop`; el CI de GitHub Actions valida cada push y pull request.

## Estado

Fase 1: entorno, modelos de las cinco apps, API GeoJSON de solo lectura, importadores de territorio e incidentes y CI.
Fuera de esta fase: interfaz web, ingesta satelital, cálculo del índice de riesgo y validación del modelo.
