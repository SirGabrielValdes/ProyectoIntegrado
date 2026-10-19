"""
Configuración del Sistema de Gestión de Requerimientos (SGR)
Municipalidad de La Serena.

Toda configuración sensible se lee desde variables de entorno (archivo .env).

- Sin .env el proyecto arranca en modo desarrollo local (DEBUG, SQLite).
- Producción/AWS: ver deploy/env.produccion.example.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(nombre, defecto=False):
    return os.environ.get(nombre, str(defecto)).strip().lower() in ("1", "true", "si", "sí", "yes")


def env_int(nombre, defecto):
    try:
        return int(os.environ.get(nombre, defecto))
    except (TypeError, ValueError):
        return defecto


def env_list(nombre, defecto=""):
    return [v.strip() for v in os.environ.get(nombre, defecto).split(",") if v.strip()]


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "").strip()
# Sin clave secreta definida se asume desarrollo local (recién clonado).
DEBUG = env_bool("DJANGO_DEBUG", not SECRET_KEY)
if not DEBUG and (not SECRET_KEY or SECRET_KEY.startswith("cambiar")):
    raise RuntimeError("Producción: defina DJANGO_SECRET_KEY en .env (ver deploy/env.produccion.example).")
if not SECRET_KEY:
    SECRET_KEY = "solo-desarrollo-local-no-usar-en-produccion"

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "")

VERSION_SGR = os.environ.get("SGR_VERSION", "v2.0.0-entrega2")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "core",
    "cuentas",
    "catalogos",
    "atenciones",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Toda ruta exige sesión salvo las marcadas con @login_not_required.
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
    "core.middleware.ContextoDelegacionMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "sgr.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.sgr",
            ],
        },
    },
]

WSGI_APPLICATION = "sgr.wsgi.application"

# --- Base de datos -----------------------------------------------------------
# Producción (AWS): MySQL/MariaDB. Desarrollo y pruebas automáticas: SQLite.
DB_ENGINE = os.environ.get("DB_ENGINE", "sqlite").lower()
if DB_ENGINE == "mysql":
    import pymysql

    pymysql.install_as_MySQLdb()
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.environ.get("DB_NAME", "sgr"),
            "USER": os.environ.get("DB_USER", "sgr"),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
            "PORT": os.environ.get("DB_PORT", "3306"),
            "OPTIONS": {"charset": "utf8mb4", "init_command": "SET sql_mode='STRICT_TRANS_TABLES'"},
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / os.environ.get("SQLITE_NAME", "db.sqlite3"),
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Caché compartida entre procesos (se usa para limitar intentos de login).
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "sgr_cache",
    }
}

# --- Autenticación -----------------------------------------------------------
AUTH_USER_MODEL = "cuentas.Usuario"
AUTHENTICATION_BACKENDS = ["cuentas.backends.UsuarioOCorreoBackend"]
LOGIN_URL = "cuentas:login"
LOGIN_REDIRECT_URL = "core:inicio"
LOGOUT_REDIRECT_URL = "cuentas:login"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "cuentas.validadores.PoliticaClaveValidator"},
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
     "OPTIONS": {"user_attributes": ("username", "correo", "nombre")}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

SESSION_COOKIE_AGE = env_int("SESSION_MINUTOS", 60) * 60
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True

# Límites de acceso y recuperación (valores referenciales del diseño; configurables).
LOGIN_MAX_INTENTOS = env_int("LOGIN_MAX_INTENTOS", 5)
LOGIN_BLOQUEO_MINUTOS = env_int("LOGIN_BLOQUEO_MINUTOS", 5)
RECUPERACION_VIGENCIA_MINUTOS = env_int("RECUPERACION_VIGENCIA_MINUTOS", 10)
RECUPERACION_ESPERA_REENVIO_SEG = env_int("RECUPERACION_ESPERA_REENVIO_SEG", 45)
RECUPERACION_MAX_INTENTOS = env_int("RECUPERACION_MAX_INTENTOS", 5)
RECUPERACION_MAX_REENVIOS = env_int("RECUPERACION_MAX_REENVIOS", 3)
RECUPERACION_MAX_SOLICITUDES_HORA = env_int("RECUPERACION_MAX_SOLICITUDES_HORA", 3)

# --- Correo (código de recuperación) -----------------------------------------
# Sin EMAIL_HOST el correo se imprime en consola (modo desarrollo).
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
if EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_PORT = env_int("EMAIL_PORT", 587)
    EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
    EMAIL_TIMEOUT = 15
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = os.environ.get("EMAIL_FROM", "SGR La Serena <no-responder@sgr.local>")

# --- Internacionalización ----------------------------------------------------
LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True

# --- Archivos estáticos ------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MESSAGE_TAGS = {40: "error"}

# --- Seguridad en producción -------------------------------------------------
if not DEBUG:
    SESSION_COOKIE_SECURE = env_bool("COOKIES_SEGURAS", False)
    CSRF_COOKIE_SECURE = env_bool("COOKIES_SEGURAS", False)
    SECURE_SSL_REDIRECT = env_bool("FORZAR_HTTPS", False)
    SECURE_HSTS_SECONDS = env_int("HSTS_SEGUNDOS", 0)
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
    if env_bool("DETRAS_DE_PROXY", True):
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"consola": {"class": "logging.StreamHandler"}},
    "loggers": {
        "sgr": {"handlers": ["consola"], "level": os.environ.get("LOG_LEVEL", "INFO")},
        "django.request": {"handlers": ["consola"], "level": "ERROR"},
    },
}
