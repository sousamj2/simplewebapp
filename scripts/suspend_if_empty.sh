#!/bin/bash
cd /var/www/appmodules/simplewebapp/Funhelpers || exit 1
PATH=/usr/local/bin:/usr/bin:/bin

/var/www/appmodules/app-env/bin/python /var/www/appmodules/simplewebapp/Funhelpers/suspend_if_empty.py \
  --instance mcserver-mem8 \
  --zone europe-west1-b \
  --state-file /var/www/appmodules/simplewebapp/scripts/suspend_if_empty_state.json \
  --summary \
  > /var/www/appmodules/simplewebapp/scripts/suspend_if_empty.log 2>&1
