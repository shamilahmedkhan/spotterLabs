import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def load_dotenv(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


load_dotenv(BASE_DIR / ".env")


def get_env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


SECRET_KEY = get_env(
    "DJANGO_SECRET_KEY",
    "django-insecure-*-h7ugvw*c+dxoozc5bm2e@)q+$@3!1pdh@itfut=0+3$_dd*0",
)
DEBUG = get_env("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = [host for host in get_env("DJANGO_ALLOWED_HOSTS", "*").split(",") if host]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "route_planner",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Chicago"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "spotterlabs-cache",
    }
}

FUEL_ROUTING = {
    "MPG": float(get_env("FUEL_MPG", "10")),
    "MAX_RANGE_MILES": float(get_env("FUEL_MAX_RANGE_MILES", "500")),
    "ROUTE_CORRIDOR_MILES": float(get_env("ROUTE_CORRIDOR_MILES", "30")),
    "ORIGIN_SEARCH_LIMIT_MILES": float(get_env("ORIGIN_SEARCH_LIMIT_MILES", "50")),
    "ROUTE_SIMPLIFY_TOLERANCE_MILES": float(
        get_env("ROUTE_SIMPLIFY_TOLERANCE_MILES", "2")
    ),
}

CENSUS_GEOCODER = {
    "BASE_URL": get_env(
        "CENSUS_GEOCODER_BASE_URL",
        "https://geocoding.geo.census.gov/geocoder",
    ),
    "BENCHMARK": get_env("CENSUS_BENCHMARK", "Public_AR_Current"),
}

NOMINATIM = {
    "BASE_URL": get_env(
        "NOMINATIM_BASE_URL",
        "https://nominatim.openstreetmap.org",
    ),
    "USER_AGENT": get_env(
        "NOMINATIM_USER_AGENT",
        "spotterlabs-fuel-route-planner/1.0 (contact: local-dev)",
    ),
}

OSRM = {
    "BASE_URL": get_env(
        "OSRM_BASE_URL",
        "https://router.project-osrm.org",
    ),
}

OPENROUTESERVICE = {
    "BASE_URL": get_env(
        "OPENROUTESERVICE_BASE_URL",
        "https://api.openrouteservice.org",
    ),
    "API_KEY": get_env("OPENROUTESERVICE_API_KEY"),
}
