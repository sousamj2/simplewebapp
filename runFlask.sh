#!/bin/bash

# Move to the script's directory to ensure relative paths work
cd "$(dirname "$0")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Set environment
export APP_ENV=dev # Enable SSM loading
VENV_PATH=$(realpath ../app-env)

# Fetch credentials from GCP early so table creation works
if [[ "${APP_ENV}" == "dev" ]]; then
    echo -e "${YELLOW}🔐 Fetching configuration from GCP Secret Manager (PASS_CONFIG)...${NC}"
    PROJECT_ID="minecraft-server-july-12"
    SECRET_JSON=$(gcloud secrets versions access latest --secret="PASS_CONFIG" --project="${PROJECT_ID}" 2>/dev/null)
    
    if [ $? -eq 0 ] && [ -n "$SECRET_JSON" ]; then
        # Export all keys from the JSON as environment variables
        while IFS='=' read -r key value; do
            export "$key"="$value"
        done < <(python3 -c "import json, sys; data = json.loads(sys.stdin.read()); [print(f'{k}={v}') for k, v in data.items()]" <<< "$SECRET_JSON")
        echo -e "${GREEN}   ✓ Credentials fetched from GCP and exported.${NC}"
        
        # Ensure Docker is up (using docker-compose for compatibility)
        echo -e "${YELLOW}🐳 Ensuring Docker containers are up...${NC}"
        (cd .. && docker-compose up -d || docker compose up -d)

        # Wait for MariaDB to be ready
        echo -e "${YELLOW}⏳ Waiting for MariaDB to be ready...${NC}"
        for i in {1..30}; do
            # Use pymysql to do a real connection check.
            # If we get Access Denied (1045), the server is alive and ready, so we count it as a success!
            if $VENV_PATH/bin/python -c "
import pymysql, sys, os
try:
    pymysql.connect(
        host='127.0.0.1',
        port=3307,
        user=os.getenv('MYSQL_USER', 'dummy'),
        password=os.getenv('MYSQL_PASSWORD', 'dummy')
    )
except pymysql.err.OperationalError as e:
    if e.args[0] == 1045: sys.exit(0)
    sys.exit(1)
except Exception:
    sys.exit(1)
" 2>/dev/null; then
                break
            fi
            echo -n "$i."
            sleep 1
        done
        echo ""
    else
        echo -e "${RED}   ✗ Failed to fetch credentials from GCP. Falling back to .env defaults.${NC}"
    fi
fi

echo -e "   🚀 Creating tables if they don't exist"

# Get absolute path to the virtual environment

$VENV_PATH/bin/python -c "import os;\
import sys;\
sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), '..')));\
sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), '../mysql')));\
from DBhelpers import DBbaseline;\
DBbaseline.setup_mysql_database();\
"

echo -e "   ✅ Tables are now up and running"
echo ""
echo ""
echo -e "${GREEN}🚀 Starting Flask Development Server${NC}"

# Set Flask environment
export FLASK_APP=app.py
export FLASK_ENV=development
export FLASK_DEBUG=1

echo -e "${YELLOW}📍 Access URLs:${NC}"
echo -e "   Local:  http://[::1]:8081"
echo -e "   Remote: https://mc.mjcrafts.pt"
echo ""
echo -e "${YELLOW}💡 Features enabled:${NC}"
echo -e "   ✅ Auto-reload on file changes"
echo -e "   ✅ Interactive debugger"
echo -e "   ✅ Detailed error pages"
echo ""
echo -e "${RED}Press Ctrl+C to stop${NC}"
echo ""

# Start Flask
# $VENV_PATH/bin/flask run --host=localhost --port=8080
$VENV_PATH/bin/flask run --host=:: --port=8081
