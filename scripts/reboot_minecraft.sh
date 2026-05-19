#!/bin/bash
# reboot_minecraft.sh - Triggers a graceful reboot of the MC server on GCP VM if it is running.

INSTANCE_NAME="mcserver-mem8"
ZONE="europe-west1-b"
PROJECT_ID="minecraft-server-july-12"

# Check if VM is running
STATUS=$(gcloud compute instances describe $INSTANCE_NAME --zone $ZONE --project $PROJECT_ID --format="value(status)" 2>/dev/null || echo "OFFLINE")

if [ "$STATUS" = "RUNNING" ]; then
    echo "$(date): Instance is RUNNING. Initiating graceful Minecraft server restart..."
    # Run bring_mc_down.sh to stop and archive logs
    gcloud compute ssh $INSTANCE_NAME --zone $ZONE --project $PROJECT_ID --quiet -- "sudo bash /home/minecraft/cronjobs/bring_mc_down.sh"
    
    # Start it back up
    echo "$(date): Starting Minecraft server back up..."
    gcloud compute ssh $INSTANCE_NAME --zone $ZONE --project $PROJECT_ID --quiet -- "sudo systemctl start mcpserver.service"
else
    echo "$(date): Instance is not running ($STATUS). Skipping restart."
fi
