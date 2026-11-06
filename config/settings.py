"""Brand-neutral publishing platform. No SMTP or email account required for core flows."""
import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=False)

def flag(key, default="false"):
    return os.getenv(key, default).strip().lower() in ("1", "yes", "true", "on")

DEBUG = flag("DJANGO_DEBUG")
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if not SECRET_KEY or SECRET_KEY == "REPLACE_WITH_RANDOM_SECRET":
    raise RuntimeError("Set DJANGO_SECRET_KEY in a private .env file before starting Django")

ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = [h.strip() for h in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if h.strip()]
SITE_NAME = os.getenv("SITE_NAME", "Working Newsroom")
SITE_TAGLINE = os.getenv("SITE_TAGLINE", "Independent reporting and announcements")
SITE_DOMAIN = os.getenv("SITE_DOMAIN", "localhost")
SITE_LANGUAGE = os.getenv("SITE_LANGUAGE", "en")
SITE_LOGO_URL = os.getenv("SITE_LOGO_URL", "")
SITE_ACCENT_COLOR = os.getenv("SITE_ACCENT_COLOR", "#076dd7")

INSTALLED_APPS = [
    "home", "newsroom", "publishers", "billing", "accounts", "website",
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sitemaps",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "wagtail.contrib.forms", "wagtail.contrib.redirects", "wagtail.contrib.sitemaps",
    "wagtail.embeds", "wagtail.sites", "wagtail.locales", "wagtail.users", "wagtail.snippets",
    "wagtail.documents", "wagtail.images", "wagtail.search", "wagtail.admin",
    "wagtail", "modelcluster", "taggit",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
    "website.middleware.PrivateAccountCacheMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
        "website.context.site_context",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {"default": dj_database_url.parse(
    os.getenv("DATABASE_URL", "postgresql://swizzle:swizzle@localhost:5432/swizzle"),
    conn_max_age=60, conn_health_checks=True,
)}
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "publishers:dashboard"
LOGOUT_REDIRECT_URL = "/"
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
WAGTAIL_SITE_NAME = SITE_NAME
WAGTAILADMIN_BASE_URL = os.getenv("WAGTAILADMIN_BASE_URL", "http://localhost:8000")
WAGTAILSEARCH_BACKENDS = {"default": {"BACKEND": "wagtail.search.backends.database"}}
WAGTAILIMAGES_MAX_UPLOAD_SIZE = 10 * 1024 * 1024

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/1")
CELERY_TASK_IGNORE_RESULT = True
NEWSROOM_AUTO_PUBLISH = flag("NEWSROOM_AUTO_PUBLISH")
NEWSROOM_ITEMS_PER_RUN = int(os.getenv("NEWSROOM_ITEMS_PER_RUN", "10"))
AI_PROVIDER = os.getenv("AI_PROVIDER", "groq")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_READER_MONTHLY_PRICE_ID = os.getenv("STRIPE_READER_MONTHLY_PRICE_ID", "")
PRESS_RELEASE_PRICE_CENTS = int(os.getenv("PRESS_RELEASE_PRICE_CENTS", "2900"))
TURNSTILE_SITE_KEY = os.getenv("TURNSTILE_SITE_KEY", "")
TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY", "")
ADSENSE_CLIENT_ID = os.getenv("ADSENSE_CLIENT_ID", "")
ADSENSE_SLOT_ID = os.getenv("ADSENSE_SLOT_ID", "")
ADS_TXT = os.getenv("ADS_TXT", "")

# Never silently deliver messages to nowhere; application uses in-dashboard messaging.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
