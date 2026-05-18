#!/bin/bash
# Move to the script's directory
cd "$(dirname "$0")"

# 1. Configuration
PROJECT_ID="minecraft-server-july-12"
VENV_PATH=$(realpath ../app-env)

# 2. Ensure Docker containers are up (Local DB)
echo "🐳 Ensuring Docker containers are up..."
(cd .. && docker-compose up -d || docker compose up -d)

# 3. Fetch configuration from GCP Secret Manager
SECRET_JSON=$(gcloud secrets versions access latest --secret="PASS_CONFIG" --project="${PROJECT_ID}" --quiet)

if [ $? -eq 0 ] && [ -n "$SECRET_JSON" ]; then
    # Export all keys from the JSON as environment variables
    while IFS='=' read -r key value; do
        export "$key"="$value"
    done < <(python3 -c "import json, sys; data = json.loads(sys.stdin.read()); [print(f'{k}={v}') for k, v in data.items()]" <<< "$SECRET_JSON")
else
    echo "CRITICAL: Failed to fetch secrets from GCP."
    exit 1
fi

# 4. Wait for the MariaDB to be ready
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
    sleep 1
done

# 5. Start the application in production mode
export APP_ENV=production
export FLASK_ENV=production
export FLASK_DEBUG=0
export FLASK_APP=app.py

exec $VENV_PATH/bin/python -m flask run --host=:: --port=8081
