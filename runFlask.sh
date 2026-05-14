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

# Fetch credentials from SSM early so table creation works
if [[ "${APP_ENV}" == "dev" ]]; then
    echo -e "${YELLOW}🔐 Fetching credentials from AWS SSM...${NC}"
    AWS_REGION="eu-south-2"
    
    # Exporting these so they are available to the process and any subprocesses
    export ROOT_MYSQL_PASSWORD=$(aws ssm get-parameter --name "/dev/ROOT_MYSQL_PASSWORD" --with-decryption --query "Parameter.Value" --output text --region $AWS_REGION 2>/dev/null || echo "")
    export MC_MYSQL_PASSWORD=$(aws ssm get-parameter --name "/dev/MC_MYSQL_PASSWORD" --with-decryption --query "Parameter.Value" --output text --region $AWS_REGION 2>/dev/null || echo "")
    export EXPL_MYSQL_PASSWORD=$(aws ssm get-parameter --name "/dev/EXPL_MYSQL_PASSWORD" --with-decryption --query "Parameter.Value" --output text --region $AWS_REGION 2>/dev/null || echo "")
    
    # Also fetch SECRET_KEY if it's missing in .env
    if [ -z "$SECRET_KEY" ] && [ -z "$FLASK_SECRET_KEY" ]; then
         export SECRET_KEY=$(aws ssm get-parameter --name "/dev/SECRET_KEY" --with-decryption --query "Parameter.Value" --output text --region $AWS_REGION 2>/dev/null || echo "")
    fi

    if [ -z "$ROOT_MYSQL_PASSWORD" ]; then
        echo -e "${RED}   ✗ Failed to fetch credentials from SSM. Falling back to .env defaults.${NC}"
    else
        echo -e "${GREEN}   ✓ Credentials fetched and exported.${NC}"
        
        # Ensure Docker is up (using docker-compose for compatibility)
        echo -e "${YELLOW}🐳 Ensuring Docker containers are up...${NC}"
        (cd .. && docker-compose up -d || docker compose up -d)

        # Wait for MariaDB to be ready
        echo -e "${YELLOW}⏳ Waiting for MariaDB to be ready...${NC}"
        for i in {1..30}; do
            if [[ "$OSTYPE" == "darwin"* ]]; then
                 # MacOS version of nc
                 nc -z -w 1 localhost 3307 && break
            else
                 # Linux version of nc
                 nc -z localhost 3307 && break
            fi
            echo -n "."
            sleep 1
        done
        echo ""
    fi
fi

echo -e "   🚀 Creating tables if they don't exist"

# Get absolute path to the virtual environment
VENV_PATH=$(realpath ../app-env)

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
