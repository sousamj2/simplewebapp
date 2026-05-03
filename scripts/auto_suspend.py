#!/home/sargedas/work/appmodules/app-env/bin/python3
import os
import sys
import subprocess
import time
from datetime import datetime, timedelta

# Ensure the appmodules directory is in sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
app_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
if app_root not in sys.path:
    sys.path.insert(0, app_root)

# Debug prints for pathing
# print(f"DEBUG AUTO-SUSPEND: script_dir={script_dir}")
# print(f"DEBUG AUTO-SUSPEND: app_root={app_root}")
# print(f"DEBUG AUTO-SUSPEND: sys.path={sys.path}")

try:
    from simplewebapp.Funhelpers.mc_server_status import get_mc_status
except ImportError as e:
    print(f"DEBUG AUTO-SUSPEND: Import error: {e}")
    sys.exit(1)

# Config (Should ideally be pulled from config.py)
INSTANCE_NAME = "mcserver-mem8"
ZONE = "europe-west1-b"
PROJECT_ID = "minecraft-server-july-12"
IDLE_THRESHOLD_MINUTES = 10

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        return result.stdout.strip()
    except Exception as e:
        print(f"DEBUG AUTO-SUSPEND: Error running command: {e}")
        return ""

def check_and_suspend():
    print(f"DEBUG AUTO-SUSPEND: [{datetime.now()}] Checking server status...")
    
    status = get_mc_status()
    
    if not status.get("online"):
        print("DEBUG AUTO-SUSPEND: Server is already offline.")
        return

    players = status.get("players_online", 0)
    print(f"DEBUG AUTO-SUSPEND: Players online: {players}")

    if players > 0:
        print("DEBUG AUTO-SUSPEND: Server is active. Skipping.")
        return

    # Players == 0, check last logout time
    print("DEBUG AUTO-SUSPEND: No players online. Checking last logout via journal...")
    
    # Use journalctl as recommended by user
    ssh_cmd = f"gcloud compute ssh {INSTANCE_NAME} --zone {ZONE} --project {PROJECT_ID} --quiet -- " \
              f"\"sudo journalctl -u mcpserver.service --grep 'left the game' -n 1 --no-pager\""
    
    output = run_cmd(ssh_cmd)
    
    if not output:
        # If no logout found in current journal, maybe server just started?
        # We should check if the server started long ago
        print("DEBUG AUTO-SUSPEND: No logout found in journal. Checking server uptime...")
        # Fallback: check how long the service has been running
        uptime_cmd = f"gcloud compute ssh {INSTANCE_NAME} --zone {ZONE} --project {PROJECT_ID} --quiet -- " \
                     f"\"sudo systemctl show mcpserver.service --property=ActiveEnterTimestamp\""
        uptime_out = run_cmd(uptime_cmd)
        if "ActiveEnterTimestamp=" in uptime_out:
            ts_str = uptime_out.split("=")[1]
            try:
                # Format: Sun 2026-05-03 10:00:00 WEST
                # We'll just parse the date part
                start_time = datetime.strptime(" ".join(ts_str.split()[1:3]), "%Y-%m-%d %H:%M:%S")
                if datetime.now() - start_time < timedelta(minutes=IDLE_THRESHOLD_MINUTES):
                    print(f"DEBUG AUTO-SUSPEND: Server started recently ({start_time}). Skipping.")
                    return
                else:
                    print(f"DEBUG AUTO-SUSPEND: Server has been running since {start_time} with no players.")
            except:
                pass
    else:
        # Parse journal line: "May 03 10:55:54 mcserver-mem8 ..."
        # Note: journalctl usually includes the year if it's old, but default is "MMM DD HH:MM:SS"
        try:
            parts = output.split()
            date_str = f"{parts[0]} {parts[1]} {parts[2]} {datetime.now().year}"
            last_logout = datetime.strptime(date_str, "%b %d %H:%M:%S %Y")
            
            # Handle year rollover if needed (rare)
            if last_logout > datetime.now():
                last_logout = last_logout.replace(year=last_logout.year - 1)
                
            idle_delta = datetime.now() - last_logout
            print(f"DEBUG AUTO-SUSPEND: Last player left at {last_logout} ({idle_delta.total_seconds()/60:.1f} min ago)")
            
            if idle_delta < timedelta(minutes=IDLE_THRESHOLD_MINUTES):
                print(f"DEBUG AUTO-SUSPEND: Idle for less than {IDLE_THRESHOLD_MINUTES} minutes. Skipping.")
                return
        except Exception as e:
            print(f"DEBUG AUTO-SUSPEND: Failed to parse journal output: {e}")
            return

    # Suspend!
    print("DEBUG AUTO-SUSPEND: IDLE THRESHOLD EXCEEDED. Suspending instance...")
    
    # 1. Stop the monitoring timer so it doesn't fire while VM is starting later
    print("DEBUG AUTO-SUSPEND: Stopping auto-suspend timer...")
    run_cmd("sudo systemctl stop mc_auto_suspend.timer")
    
    # 2. Suspend the instance
    suspend_cmd = f"gcloud compute instances suspend {INSTANCE_NAME} --zone {ZONE} --project {PROJECT_ID} --quiet"
    run_cmd(suspend_cmd)
    print("DEBUG AUTO-SUSPEND: Suspend command issued.")

if __name__ == "__main__":
    check_and_suspend()
