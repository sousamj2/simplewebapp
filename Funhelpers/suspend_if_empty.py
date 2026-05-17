#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from mc_server_status import get_mc_status
from mc_rcon import run_rcon_command

# Add app modules to path for DB helpers
script_dir = Path(__file__).parent
app_root = script_dir.parent.parent
if str(app_root) not in sys.path:
    sys.path.insert(0, str(app_root))
if str(script_dir.parent) not in sys.path:
    sys.path.insert(0, str(script_dir.parent))

from mysql.DBhelpers import update_mc_stats, getEmailFromIgn

STATE_FILE = Path('/var/www/appmodules/simplewebapp/scripts/suspend_if_empty_state.json')
INSTANCE_NAME = 'mcserver-mem8'
ZONE = 'europe-west1-b'
REMOTE_SHUTDOWN_SCRIPT = '/home/minecraft/cronjobs/bring_mc_down.sh'


def run_command(cmd, dry_run=False, timeout=180): # Increased timeout for archival
    if dry_run:
        return {'ok': True, 'stdout': '', 'stderr': '', 'returncode': 0}

    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return {
            'ok': res.returncode == 0,
            'stdout': res.stdout.strip(),
            'stderr': res.stderr.strip(),
            'returncode': res.returncode
        }
    except Exception as e:
        return {'ok': False, 'stdout': '', 'stderr': str(e), 'returncode': -1}


def get_instance_ipv6(instance, zone, project=None):
    # Try external IPv6 first
    cmd = f"gcloud compute instances describe {instance} --zone {zone} "
    if project:
        cmd += f"--project {project} "
    cmd += "--format='get(networkInterfaces[0].ipv6AccessConfigs[0].externalIpv6)'"
    res = run_command(cmd)
    ext_ipv6 = res.get('stdout', '').strip()
    
    if ext_ipv6:
        return ext_ipv6
        
    # Fallback to internal IPv6
    cmd = f"gcloud compute instances describe {instance} --zone {zone} "
    if project:
        cmd += f"--project {project} "
    cmd += "--format='get(networkInterfaces[0].ipv6Address)'"
    res = run_command(cmd)
    return res.get('stdout', '').strip()


def gcloud_ssh_command(instance, zone, remote_command, project=None):
    ipv6 = get_instance_ipv6(instance, zone, project)
    base = f"gcloud compute ssh {instance} --zone {zone} "
    if project:
        base += f"--project {project} "
    if ipv6:
        base += f"--address='[{ipv6}]' "
    base += f"--quiet -- '{remote_command}'"
    return base


def get_instance_status(instance, zone, project=None):
    cmd = f"gcloud compute instances describe {instance} --zone {zone} "
    if project:
        cmd += f"--project {project} "
    cmd += "--format='get(status)'"
    res = run_command(cmd)
    return res.get('stdout', 'UNKNOWN')


def run_gcloud_suspend(instance, zone, project=None, dry_run=False):
    cmd = f"gcloud compute instances suspend {instance} --zone {zone} --quiet"
    if project:
        cmd += f" --project {project}"
    return run_command(cmd, dry_run=dry_run)


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding='utf-8')


def sync_cache_to_db(instance: str, zone: str, project: str | None):
    """
    Reads usecache_0.json from the remote server and updates the local DB.
    Must be called BEFORE bring_mc_down.sh archives/deletes the file.
    """
    cat_cmd = gcloud_ssh_command(instance, zone, "cat /home/minecraft/cronjobs/usecache_0.json", project)
    res = run_command(cat_cmd)
    if not res.get('ok'):
        return
    
    try:
        cache = json.loads(res.get('stdout', '{}'))
        for uuid, data in cache.items():
            ign = data.get('player')
            if not ign:
                continue
            
            email = getEmailFromIgn(ign)
            if not email:
                continue
            
            last_online = data.get('measured_at')
            update_mc_stats(
                email,
                uuid,
                data.get('rank', 'NR'),
                "NA", 
                "NA", 
                last_online
            )
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description='Suspend a GCE VM when the Minecraft server is online with zero players.')
    parser.add_argument('--instance', default=INSTANCE_NAME)
    parser.add_argument('--zone', default=ZONE)
    parser.add_argument('--project', default=None)
    parser.add_argument('--shutdown-script', default=REMOTE_SHUTDOWN_SCRIPT)
    parser.add_argument('--archive-script', help='Deprecated: Archival is now handled by the shutdown script.')
    parser.add_argument('--state-file', default=STATE_FILE)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--summary', action='store_true')
    args = parser.parse_args()

    measured_at = datetime.now(timezone.utc).astimezone().isoformat()

    status_vm = get_instance_status(args.instance, args.zone, args.project)
    if status_vm != 'RUNNING':
        result = {
            'measured_at': measured_at,
            'instance': args.instance,
            'zone': args.zone,
            'status_vm': status_vm,
            'message': f'Instance is not RUNNING (current status: {status_vm}). Skipping.'
        }
        if args.summary:
            print(json.dumps(result))
        else:
            print(json.dumps(result, indent=2, sort_keys=True))
        sys.exit(0)

    status = get_mc_status()
    online = bool(status.get('online'))
    players_online = int(status.get('players_online', 0) or 0)
    
    # We should suspend if the server is online but NO players are connected
    should_suspend = online and players_online == 0

    # Ensure we have data to sync before we consider the "quiet" state valid
    check_cmd = gcloud_ssh_command(
        args.instance,
        args.zone,
        'test -f /home/minecraft/cronjobs/usecache_0.json',
        args.project,
    )
    check_result = run_command(check_cmd)
    print(f"DEBUG: check_cmd={check_cmd}")
    print(f"DEBUG: check_result={check_result}")
    cache_exists = check_result.get('ok', False)
    
    if not cache_exists:
        # If no cache exists, maybe it was just started or already cleaned.
        # We err on the side of caution and don't suspend if we can't verify history.
        should_suspend = False

    shutdown_result = None
    action = None

    if should_suspend:
        # 1. Sync stats to DB first while we have the file!
        sync_cache_to_db(args.instance, args.zone, args.project)
        
        # 2. Trigger the server-side shutdown and archival script
        # This handles unbanning, whitelist, save, stop, and log archival.
        shutdown_cmd = gcloud_ssh_command(
            args.instance,
            args.zone,
            f'sudo bash {args.shutdown_script}',
            args.project,
        )
        shutdown_result = run_command(shutdown_cmd, dry_run=args.dry_run)

        # 3. If shutdown was successful, suspend the VM
        if shutdown_result.get('ok', False):
            action = run_gcloud_suspend(args.instance, args.zone, args.project, args.dry_run)

    result = {
        'measured_at': measured_at,
        'status': status,
        'online': online,
        'players_online': players_online,
        'should_suspend': should_suspend,
        'instance': args.instance,
        'zone': args.zone,
        'project': args.project,
        'shutdown_script': args.shutdown_script,
        'shutdown': shutdown_result,
        'action': action,
    }
    save_json(Path(args.state_file), result)

    if args.summary:
        print(json.dumps(result))
    else:
        print(json.dumps(result, indent=2, sort_keys=True))

    if any(step and not step.get('ok', False) for step in [shutdown_result, action]):
        sys.exit(1)


if __name__ == '__main__':
    main()
