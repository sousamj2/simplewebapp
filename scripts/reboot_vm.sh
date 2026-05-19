#!/bin/bash
# reboot_vm.sh - Cleanly reboot the GCP VM and restart Minecraft, resuming it first if suspended.

INSTANCE_NAME="mcserver-mem8"
ZONE="europe-west1-b"
PROJECT_ID="minecraft-server-july-12"

echo "$(date): Starting scheduled VM reboot sequence..."

# Check VM status
STATUS=$(gcloud compute instances describe $INSTANCE_NAME --zone $ZONE --project $PROJECT_ID --format="value(status)" 2>/dev/null || echo "UNKNOWN")
echo "$(date): Current VM status is $STATUS"

if [ "$STATUS" = "SUSPENDED" ]; then
    echo "$(date): Resuming suspended VM..."
    gcloud compute instances resume $INSTANCE_NAME --zone $ZONE --project $PROJECT_ID --quiet
    # Wait for VM to be RUNNING
    sleep 15
elif [ "$STATUS" = "TERMINATED" ]; then
    echo "$(date): Starting terminated VM..."
    gcloud compute instances start $INSTANCE_NAME --zone $ZONE --project $PROJECT_ID --quiet
    sleep 15
elif [ "$STATUS" = "RUNNING" ]; then
    echo "$(date): VM is running. Gracefully stopping Minecraft first..."
    gcloud compute ssh $INSTANCE_NAME --zone $ZONE --project $PROJECT_ID --quiet -- "sudo bash /home/minecraft/cronjobs/bring_mc_down.sh"
fi

# Wait for VM to be fully responsive to SSH
echo "$(date): Waiting for SSH to be responsive..."
for i in {1..30}; do
    if gcloud compute ssh $INSTANCE_NAME --zone $ZONE --project $PROJECT_ID --quiet -- "echo ready" &>/dev/null; then
        echo "$(date): SSH is responsive."
        break
    fi
    sleep 5
done

# Perform OS reboot
echo "$(date): Issuing reboot command to the VM OS..."
gcloud compute ssh $INSTANCE_NAME --zone $ZONE --project $PROJECT_ID --quiet -- "sudo reboot" || true

# Wait for VM to come back online after reboot
echo "$(date): Waiting for VM to come back online..."
sleep 30
for i in {1..30}; do
    # Check status
    NEW_STATUS=$(gcloud compute instances describe $INSTANCE_NAME --zone $ZONE --project $PROJECT_ID --format="value(status)" 2>/dev/null || echo "UNKNOWN")
    if [ "$NEW_STATUS" = "RUNNING" ]; then
        if gcloud compute ssh $INSTANCE_NAME --zone $ZONE --project $PROJECT_ID --quiet -- "echo ready" &>/dev/null; then
            echo "$(date): VM is back online and SSH is ready."
            break
        fi
    fi
    sleep 10
done

# Start Minecraft service
echo "$(date): Starting Minecraft service..."
gcloud compute ssh $INSTANCE_NAME --zone $ZONE --project $PROJECT_ID --quiet -- "sudo systemctl start mcpserver.service"

# Start the auto-suspend timer on EC2-2 in case it was stopped
echo "$(date): Ensuring auto-suspend timer is active on EC2-2..."
sudo systemctl start mc_auto_suspend.timer

echo "$(date): VM reboot sequence completed."
