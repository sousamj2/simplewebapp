#!/bin/bash
# save_minecraft.sh - Triggers a save-all command on the GCP VM if it is running.

INSTANCE_NAME="mcserver-mem8"
ZONE="europe-west1-b"
PROJECT_ID="minecraft-server-july-12"

STATUS=$(gcloud compute instances describe $INSTANCE_NAME --zone $ZONE --project $PROJECT_ID --format="value(status)" 2>/dev/null || echo "OFFLINE")

if [ "$STATUS" = "RUNNING" ]; then
    echo "$(date): Instance is RUNNING. Triggering save-all..."
    gcloud compute ssh $INSTANCE_NAME --zone $ZONE --project $PROJECT_ID --quiet -- "
        SERVER_PROPS='/home/minecraft/server.properties'
        if [ -f '\$SERVER_PROPS' ]; then
            PORT=\$(grep '^rcon.port=' '\$SERVER_PROPS' | cut -d'=' -f2 | tr -d '\r')
            PASSWORD=\$(grep '^rcon.password=' '\$SERVER_PROPS' | cut -d'=' -f2 | tr -d '\r')
            /usr/local/bin/mcrcon -H localhost -P '\$PORT' -p '\$PASSWORD' 'save-all'
        else
            echo 'Error: server.properties not found'
        fi
    "
else
    echo "$(date): Instance is not running ($STATUS). Skipping save."
fi
