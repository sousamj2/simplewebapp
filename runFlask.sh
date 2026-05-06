#!/bin/bash

# Move to the script's directory to ensure relative paths work
cd "$(dirname "$0")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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
echo -e "   Local:  http://localhost:8080"
echo -e "   Local:  https://mc.mjcrafts.pt"
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
$VENV_PATH/bin/flask run --host=0.0.0.0 --port=8081
