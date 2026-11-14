from pathlib import Path

from dotenv import load_dotenv

from config.entorno import env_bool, env_lista, env_requerida

BASE_DIR = Path(__file__).resolve().parent.parent

# Fuera de Docker se lee el .env de la raíz del repositorio; el entorno real tiene prioridad.
load_dotenv(BASE_DIR.parent / ".env", override=False)

SECRET_KEY = env_requerida("DJANGO_SECRET_KEY")
DEBUG = env_bool("DJANGO_DEBUG")
ALLOWED_HOSTS = env_lista("DJANGO_ALLOWED_HOSTS")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.gis",
    "rest_framework",
    "corsheaders",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": env_requerida("POSTGRES_DB"),
        "USER": env_requerida("POSTGRES_USER"),
        "PASSWORD": env_requerida("POSTGRES_PASSWORD"),
        "HOST": env_requerida("POSTGRES_HOST"),
        "PORT": env_requerida("POSTGRES_PORT"),
        "TEST": {"TEMPLATE": "template_postgis"},
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LANGUAGE_CODE = "es"
TIME_ZONE = "America/La_Paz"
USE_I18N = True
USE_TZ = True

# Cerrado por defecto: cada vista pública declara AllowAny de forma explícita.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}

# CORS solo para la API pública de lectura; nunca se autorizan todos los orígenes.
CORS_URLS_REGEX = r"^/api/.*$"
CORS_ALLOWED_ORIGINS = env_lista("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_METHODS = ("GET", "HEAD", "OPTIONS")
