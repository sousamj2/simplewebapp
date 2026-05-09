#!/bin/bash
cd /var/www/appmodules/simplewebapp/Funhelpers || exit 1
PATH=/usr/local/bin:/usr/bin:/bin

# Pre-check: Only run if the instance is actually RUNNING to avoid timeouts
if ! gcloud compute instances list --filter="name:mcserver-mem8" --format="value(status)" | grep -q "RUNNING"; then
  echo "$(date): Instance mcserver-mem8 is not running. Skipping." >> /var/www/appmodules/simplewebapp/scripts/suspend_if_empty.log
  exit 0
fi

/var/www/appmodules/app-env/bin/python /var/www/appmodules/simplewebapp/Funhelpers/suspend_if_empty.py \
  --instance mcserver-mem8 \
  --zone europe-west1-b \
  --archive-script /home/minecraft/cronjobs/archive_cronjobs.sh \
  --state-file /var/www/appmodules/simplewebapp/scripts/suspend_if_empty_state.json \
  --summary \
  > /var/www/appmodules/simplewebapp/scripts/suspend_if_empty.log 2>&1
