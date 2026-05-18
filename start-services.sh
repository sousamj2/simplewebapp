#!/bin/bash
# Fetches credentials from GCP Secret Manager, then starts docker-compose.
set -e

# Move to the script's directory
cd "$(dirname "$0")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🔐 Fetching configuration from GCP Secret Manager (PASS_CONFIG)...${NC}"

PROJECT_ID="minecraft-server-july-12"
SECRET_JSON=$(gcloud secrets versions access latest --secret="PASS_CONFIG" --project="${PROJECT_ID}" --quiet)

if [ $? -ne 0 ] || [ -z "$SECRET_JSON" ]; then
    echo -e "${RED}   ✗ Failed to fetch secret from GCP.${NC}"
    exit 1
fi

# Path for the environment file
ENV_FILE="./.env.gcp"
> "$ENV_FILE"

# Export and save keys
while IFS='=' read -r key value; do
    export "$key"="$value"
    echo "$key=$value" >> "$ENV_FILE"
done < <(python3 -c "import json, sys; data = json.loads(sys.stdin.read()); [print(f'{k}={v}') for k, v in data.items()]" <<< "$SECRET_JSON")

chmod 600 "$ENV_FILE"
echo -e "${GREEN}✅ Credentials saved to $ENV_FILE${NC}"

echo -e "${YELLOW}🐳 Starting docker-compose...${NC}"
# Use the docker-compose.yml in the parent directory
docker-compose -f ../docker-compose.yml up -d || docker compose -f ../docker-compose.yml up -d

# Wait for MariaDB to be ready
echo -e "${YELLOW}⏳ Waiting for MariaDB to be ready...${NC}"
for i in {1..30}; do
    # Use pymysql to do a real connection check, as 'nc' succeeds too early due to docker-proxy
    if ../app-env/bin/python -c "import pymysql, os; pymysql.connect(host=os.getenv('MYSQL_HOST', '127.0.0.1'), port=int(os.getenv('MYSQL_PORT', 3307)), user=os.getenv('MYSQL_USER'), password=os.getenv('MYSQL_PASSWORD'))" 2>/dev/null; then
         break
    fi
    echo -n "."
    sleep 1
done
echo -e "\n${GREEN}✅ Database is ready.${NC}"
