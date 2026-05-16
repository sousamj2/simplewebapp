import os
import platform
from typing import Dict, Optional

# Optional: keep dotenv for local usage only
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

print("DEBUG: config.py is being imported", flush=True)


APP_NAME = os.getenv("APP_NAME", "explicolivais")
APP_ENV = os.getenv("APP_ENV","local")  # "production" or "local" or "testing"


def _load_from_env() -> Dict[str, str]:
    # Local/dev: load .env if library available
    print(f"DEBUG: CWD is {os.getcwd()}", flush=True)
    if load_dotenv:
        # Search for .env in current directory and parent directory
        dotenv_path = os.path.join(os.getcwd(), '.env')
        if not os.path.exists(dotenv_path):
            dotenv_path = os.path.join(os.getcwd(), '..', '.env')
            
        if os.path.exists(dotenv_path):
            print(f"DEBUG: Loading .env from {os.path.abspath(dotenv_path)}", flush=True)
            load_dotenv(dotenv_path, override=True) # Force override
        else:
            print("DEBUG: .env file not found in current or parent directory", flush=True)
            load_dotenv() # Fallback to default
            
    res = dict(os.environ)
    print(f"DEBUG: RCON_PASSWORD in os.environ: {'Yes' if 'RCON_PASSWORD' in res else 'No'}", flush=True)
    return res

def _settings() -> Dict[str, str]:
    # Always load .env as baseline
    print("[CONFIG] Loading baseline config from local .env", flush=True)
    settings = _load_from_env()
    
    # OS environment now contains both .env values and any GCP secrets
    # exported by the shell script (runFlask.sh or start-services.sh).
    return dict(os.environ)

# Centralized lookup dictionary
SETTINGS = _settings()

def _get(key: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    val = SETTINGS.get(key, default)
    if required and (val is None or val == ""):
        raise ValueError(f"{key} environment variable must be set")
    return val

class Config:
    # Flask
    SECRET_KEY = _get("FLASK_SECRET_KEY") or _get("SECRET_KEY", required=True)

    # Admin config
    ADMIN_EMAIL = _get("ADMINDB_EMAIL") or _get("ADMIN_EMAIL") or "admin@example.com"
    if ADMIN_EMAIL:
        ADMIN_EMAIL = ADMIN_EMAIL.lower()

    # Database
    DATABASE_URI = _get("DATABASE_URI", "sqlite:///default.db")

    # OAuth2 (Google)
    CLIENT_ID = _get("MC_SECRET_CLIENT_KEY") or _get("SECRET_CLIENT_KEY")
    CLIENT_SECRET = _get("MC_SECRET_CLIENT_SECRET") or _get("SECRET_CLIENT_SECRET")

    # print(CLIENT_ID)
    # print(CLIENT_SECRET)

    # Use separate redirect for production if provided, else default local
    REDIRECT_URI = _get("MC_OAUTH_REDIRECT_URI") or _get("OAUTH_REDIRECT_URI", "http://localhost:8081/oauth2callback")

    AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    SCOPE = "openid email profile"

    # Mail (no-reply)
    MAIL_SERVER = _get("MC_MAIL_SERVER")
    MAIL_PORT = int(_get("MAIL_PORT", "465"))
    MAIL_USE_SSL = (_get("MAIL_USE_SSL", "True") == "True")
    MAIL_USERNAME = _get("MC_MAIL_USERNAME")
    MAIL_PASSWORD = _get("MC_MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = _get("MC_MAIL_DEFAULT_SENDER")

    # Google Cloud Mail Relay
    GOOGLE_MAIL_RELAY_URL = _get("GOOGLE_MAIL_RELAY_URL", "https://mail-relay-783543567741.europe-southwest1.run.app")
    SECURITY_PASSWORD_SALT = _get("SECURITY_PASSWORD_SALT")

    # Google Calendar service account
    SERVICE_ACCOUNT_FILE = _get("SERVICE_ACCOUNT_FILE", "./primeiro-contact-account.json")
    SCOPES = ["https://www.googleapis.com/auth/calendar"]
    CALENDAR_ID = _get("CALENDAR_ID", "CHANGE_ME")

    # Scheduling
    MAX_SLOTS_PER_TIME = int(_get("MAX_SLOTS_PER_TIME", "4"))
    APPOINTMENT_DURATION = int(_get("APPOINTMENT_DURATION", "10"))
    WEEKLY_SCHEDULE = {
        0: [("15:00", "17:00")],
        1: [("08:00", "10:00"), ("10:00", "12:00"), ("14:00", "16:00"), ("16:00", "18:00"), ("18:00", "20:00")],
        2: [("08:00", "10:00"), ("10:00", "12:00"), ("14:00", "16:00"), ("16:00", "18:00"), ("18:00", "20:00")],
        3: [("08:00", "10:00"), ("10:00", "12:00"), ("14:00", "16:00"), ("16:00", "18:00"), ("18:00", "20:00")],
        4: [("08:00", "10:00"), ("10:00", "12:00"), ("14:00", "16:00"), ("16:00", "18:00"), ("18:00", "20:00")],
        5: [("08:00", "10:00"), ("10:00", "12:00"), ("14:00", "16:00"), ("16:00", "18:00"), ("18:00", "20:00")],
        6: [("08:00", "10:00"), ("10:00", "12:00"), ("13:00", "15:00")],
    }

    # RDS Connection to MySQL
    MYSQL_PASSWORD = _get("MC_MYSQL_PASSWORD") or _get("MYSQL_PASSWORD")
    MYSQL_HOST     = _get("MC_MYSQL_HOST") or _get("MYSQL_HOST")
    MYSQL_USER     = _get("MC_MYSQL_USER") or _get("MYSQL_USER") or "admin"
    MYSQL_DBNAME   = _get("MC_MYSQL_DBNAME") or "mc_mjcrafts"
    MYSQL_PORT     = int(_get("MC_MYSQL_PORT") or _get("MYSQL_PORT") or "3306")

    if not MYSQL_PASSWORD or not MYSQL_USER:
        print("[CONFIG] CRITICAL ERROR: mc_mjcrafts Database credentials (MYSQL_USER or MYSQL_PASSWORD) are missing. Please check AWS SSM or local .env.", flush=True)
        import sys
        sys.exit(1)

    # RCON Config
    RCON_HOST = _get("RCON_HOST", "35.210.3.240")
    RCON_PORT = int(_get("RCON_PORT", "25575"))
    RCON_PASSWORD = _get("RCON_PASSWORD")

    # GCP Config
    GCP_INSTANCE_NAME = _get("GCP_INSTANCE_NAME", "mcserver-mem8")
    GCP_ZONE = _get("GCP_ZONE", "europe-west1-b")

    DEBUG = False
    TESTING = False

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    
    # Production-grade Database connection pooling
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 10,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
    }

    # Security headers and session cookies
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_HTTPONLY = True


class DevelopmentConfig(Config):
    DEBUG = True
    DEVELOPMENT = True


class TestingConfig(Config):
    TESTING = True
    DEBUG = True


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
