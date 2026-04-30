import os
import platform
from typing import Dict, Optional

# Optional: keep dotenv for local usage only
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# Optional import for AWS SSM on EC2/production
def _import_boto3():
    try:
        import boto3
        return boto3
    except ImportError:
        return None

APP_NAME = os.getenv("APP_NAME", "explicolivais")
APP_ENV = os.getenv("APP_ENV","dev")  # "production" or "development" or "testing"

# Heuristic to decide environment if APP_ENV not set
def _is_aws_host() -> bool:
    if APP_ENV:
        return APP_ENV.lower() == "dev"
    sysname = platform.system()
    nodename = platform.node()  # e.g., ip-xx-xx-xx-xx for EC2
    return sysname == "Linux" and nodename.startswith("ip-") and ".compute.internal" in nodename

def _load_from_env() -> Dict[str, str]:
    # Local/dev: load .env if library available
    if load_dotenv:
        load_dotenv()
    return dict(os.environ)

def _load_from_ssm(prefix: str = f"/{APP_ENV}/") -> Dict[str, str]:
    boto3 = _import_boto3()
    if not boto3:
        raise RuntimeError("boto3 not installed; required to load from SSM on AWS")

    ssm = boto3.client("ssm", region_name=os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "eu-south-2")))
    params: Dict[str, str] = {}
    next_token: Optional[str] = None

    # Retrieve all parameters under a prefix. Use SecureString decryption.
    while True:
        kwargs = {
            "Path": prefix,
            "Recursive": True,
            "WithDecryption": True,
            "MaxResults": 10,
        }
        if next_token:
            kwargs["NextToken"] = next_token
        resp = ssm.get_parameters_by_path(**kwargs)
        for p in resp.get("Parameters", []):
            # Convert name '/app/KEY' -> 'KEY'
            key = p["Name"].split("/")[-1]
            params[key] = p["Value"]
        next_token = resp.get("NextToken")
        if not next_token:
            break
    return params

def _settings() -> Dict[str, str]:
    if _is_aws_host():
        return _load_from_ssm(prefix=os.getenv("SSM_PREFIX", f"/{APP_ENV}/"))
    return _load_from_env()

# Centralized lookup dictionary
SETTINGS = _settings()

def _get(key: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    val = SETTINGS.get(key, default)
    if required and (val is None or val == ""):
        raise ValueError(f"{key} environment variable must be set")
    return val

class Config:
    # Flask
    SECRET_KEY = _get("FLASK_SECRET_KEY", required=True)

    # Admin config
    ADMIN_EMAIL = _get("ADMINDB_EMAIL", required=True)
    if ADMIN_EMAIL:
        ADMIN_EMAIL = ADMIN_EMAIL.lower()

    # Database
    DATABASE_URI = _get("DATABASE_URI", "sqlite:///default.db")

    # OAuth2 (Google)
    CLIENT_ID = _get("SECRET_CLIENT_KEY")
    CLIENT_SECRET = _get("SECRET_CLIENT_SECRET")

    # print(CLIENT_ID)
    # print(CLIENT_SECRET)

    # Use separate redirect for production if provided, else default local
    REDIRECT_URI = _get("OAUTH_REDIRECT_URI", "http://localhost:8080/oauth2callback")

    AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    SCOPE = "openid email profile"

    # Mail (no-reply)
    MAIL_SERVER = _get("MAIL_SERVER")
    MAIL_PORT = int(_get("MAIL_PORT", "465"))
    MAIL_USE_SSL = (_get("MAIL_USE_SSL", "True") == "True")
    MAIL_USERNAME = _get("MAIL_USERNAME")
    MAIL_PASSWORD = _get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = _get("MAIL_DEFAULT_SENDER")

    # Optional secondary secret items
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
    MYSQL_PASSWORD = _get("MYSQL_PASSWORD")
    MYSQL_HOST     = _get("MYSQL_HOST")
    MYSQL_USER     = "admin"
    MYSQL_DBNAME   = "explicolivais"
    MYSQL_PORT     = 3306
    # print(MYSQL_PASSWORD)
    # print(MYSQL_HOST    )
    # print(MYSQL_USER    )
    # print(MYSQL_DBNAME  )
    # print(MYSQL_PORT    )
    # print()


    DEBUG = False
    TESTING = False

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

class TestingConfig(Config):
    TESTING = True
    DEBUG = True

config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
