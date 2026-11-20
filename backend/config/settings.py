import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
from dotenv import load_dotenv

load_dotenv(BASE_DIR.parent / ".env")


def env_bool(name, default=False):
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes"}


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "local-development-key-change-before-deploy")
DEBUG = env_bool("DJANGO_DEBUG", True)
if not DEBUG and (SECRET_KEY == "local-development-key-change-before-deploy" or SECRET_KEY.startswith("change-this")):
    raise RuntimeError("Set DJANGO_SECRET_KEY to a unique secret before running with DJANGO_DEBUG=False.")
ALLOWED_HOSTS = [host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if host.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "cloudinary_storage",  # must come BEFORE django.contrib.staticfiles
    "django.contrib.staticfiles",
    "cloudinary",  # must come AFTER django.contrib.staticfiles
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

if os.getenv("DB_ENGINE", "sqlite").lower() == "postgresql":
    DATABASES = {"default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", ""),
        "USER": os.getenv("DB_USER", ""),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "CONN_MAX_AGE": 60,
    }}
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}

AUTH_USER_MODEL = "api.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Kampala"
USE_I18N = True
USE_TZ = True

# Static files (served by WhiteNoise)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Media / uploads (stored on Cloudinary)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

CLOUDINARY_STORAGE = {
    "CLOUD_NAME": os.getenv("CLOUDINARY_CLOUD_NAME", ""),
    "API_KEY": os.getenv("CLOUDINARY_API_KEY", ""),
    "API_SECRET": os.getenv("CLOUDINARY_API_SECRET", ""),
}

STORAGES = {
    "default": {"BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework_simplejwt.authentication.JWTAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": ("rest_framework.throttling.AnonRateThrottle", "rest_framework.throttling.UserRateThrottle"),
    "DEFAULT_THROTTLE_RATES": {"anon": "30/min", "user": "120/min"},
}
SIMPLE_JWT = {"AUTH_HEADER_TYPES": ("Bearer",), "ACCESS_TOKEN_LIFETIME": __import__("datetime").timedelta(minutes=30)}
SPECTACULAR_SETTINGS = {"TITLE": "AgriCloud AI API", "DESCRIPTION": "Farm management and NASA POWER climate intelligence.", "VERSION": "1.0.0"}
CORS_ALLOWED_ORIGINS = [os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")]

# Email
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend" if os.getenv("EMAIL_HOST_USER") else "django.core.mail.backends.console.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() in {"1", "true", "yes"}
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "AgriCloud AI <noreply@agricloud.ai>")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
NASA_POWER_BASE_URL = os.getenv("NASA_POWER_BASE_URL", "https://power.larc.nasa.gov/api/temporal/daily/point")
NASA_POWER_TIMEOUT = int(os.getenv("NASA_POWER_TIMEOUT", "20"))
OPEN_METEO_BASE_URL = os.getenv("OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1/forecast")
OPEN_METEO_TIMEOUT = int(os.getenv("OPEN_METEO_TIMEOUT", "15"))
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_BASE_URL = os.getenv("LLM_API_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "")
CROP_VISION_MODEL = os.getenv("CROP_VISION_MODEL", "")
CROP_VISION_ENABLED = env_bool("CROP_VISION_ENABLED", True)
CROP_VISION_PROVIDER = os.getenv("CROP_VISION_PROVIDER", "openai-compatible").strip().lower()
CROP_VISION_API_KEY = os.getenv("CROP_VISION_API_KEY") or LLM_API_KEY
CROP_VISION_API_URL = os.getenv("CROP_VISION_API_URL", "https://detect.roboflow.com")
CROP_VISION_TIMEOUT = int(os.getenv("CROP_VISION_TIMEOUT", "45"))
IRRIGATION_ENABLED = env_bool("IRRIGATION_ENABLED", True)
YIELD_PREDICTION_ENABLED = env_bool("YIELD_PREDICTION_ENABLED", True)
MARKET_INTELLIGENCE_ENABLED = env_bool("MARKET_INTELLIGENCE_ENABLED", True)
MARKET_DATA_CSV_URL = os.getenv(
    "MARKET_DATA_CSV_URL",
    "https://data.humdata.org/dataset/883929b1-521e-4834-97f5-0ccc2df75b89/resource/e082d683-cad5-4dcd-bf54-db76ae254d33/download/wfp_food_prices_uga.csv",
)
MARKET_DATA_TIMEOUT = int(os.getenv("MARKET_DATA_TIMEOUT", "20"))
MARKET_DATA_CACHE_SECONDS = int(os.getenv("MARKET_DATA_CACHE_SECONDS", "21600"))
AGRICULTURE_KNOWLEDGE_CONTEXT = os.getenv("AGRICULTURE_KNOWLEDGE_CONTEXT", "")

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    CSRF_TRUSTED_ORIGINS = [
        origin.strip()
        for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
        if origin.strip()
    ]