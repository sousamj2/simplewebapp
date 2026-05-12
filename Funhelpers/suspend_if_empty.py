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
from simplewebapp.app import create_app

STATE_FILE = Path('/var/www/appmodules/simplewebapp/scripts/suspend_if_empty_state.json')
INSTANCE_NAME = 'mcserver-mem8'
ZONE = 'europe-west1-b'
REMOTE_ARCHIVE_SCRIPT = '/home/minecraft/cronjobs/archive_cronjobs.sh'


def run_command(cmd, dry_run=False, timeout=120):
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


def gcloud_ssh_command(instance, zone, remote_command, project=None):
    base = f"gcloud compute ssh {instance} --zone {zone} "
    if project:
        base += f"--project {project} "
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


def shutdown_minecraft(instance: str, zone: str, project: str | None, dry_run: bool):
    """
    Saves the world and stops the Minecraft server gracefully.
    """
    run_rcon_command("save-all")
    run_rcon_command("stop")
    
    # Also ensure systemd service is stopped
    stop_svc_cmd = gcloud_ssh_command(instance, zone, "sudo systemctl stop mcpserver.service", project)
    return run_command(stop_svc_cmd, dry_run=dry_run)


def sync_cache_to_db(instance: str, zone: str, project: str | None):
    """
    Reads usecache_0.json from the remote server and updates the local DB.
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
            
            # Fetch more stats via RCON if possible, but here we likely only have what's in JSON
            # The user wants to update the DB with _0 file info.
            last_online = data.get('measured_at')
            # If they were in the cache, they were online recently.
            update_mc_stats(
                email,
                uuid,
                data.get('rank', 'NR'),
                "NA", # bank not in usecache JSON usually
                "NA", # claims not in usecache JSON usually
                last_online
            )
    except Exception as e:
        pass


def unban_afk_players(instance: str, zone: str, project: str | None):
    cat_cmd = gcloud_ssh_command(instance, zone, "cat /home/minecraft/banned-players.json", project)
    res = run_command(cat_cmd)
    if not res.get('ok'):
        return
    
    try:
        banned = json.loads(res.get('stdout', '[]'))
        if not banned:
            return

        for entry in banned:
            created_str = entry.get('created')
            expires_str = entry.get('expires')
            name = entry.get('name')
            
            if not created_str or not expires_str or not name:
                continue
            
            # Format: 2026-05-09 13:16:02 +0000
            fmt = "%Y-%m-%d %H:%M:%S %z"
            try:
                created = datetime.strptime(created_str, fmt)
                expires = datetime.strptime(expires_str, fmt)
                
                duration = (expires - created).total_seconds()
                if duration < 420: # 7 minutes (420 seconds)
                    run_rcon_command(f"pardon {name}")
                    
                    # Also scrub them from the caches to prevent immediate re-ban on restart
                    uuid = entry.get('uuid')
                    scrub_py = (
                        "import json; from pathlib import Path; "
                        "paths = ['/home/minecraft/cronjobs/usecache_0.json', "
                        "'/home/minecraft/cronjobs/usecache_5.json', "
                        "'/home/minecraft/cronjobs/usecache_10.json']; "
                        f"target_uuid = '{uuid}'; "
                        "for p in [Path(x) for x in paths]: "
                        "if p.exists(): "
                        "try: "
                        "data = json.loads(p.read_text()); "
                        "if target_uuid in data: "
                        "del data[target_uuid]; "
                        "p.write_text(json.dumps(data, indent=2)); "
                        "except: pass"
                    )
                    scrub_cmd = gcloud_ssh_command(instance, zone, f"sudo python3 -c \"{scrub_py}\"", project)
                    run_command(scrub_cmd)
            except ValueError:
                pass
                
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description='Suspend a GCE VM when the Minecraft server is online with zero players.')
    parser.add_argument('--instance', default=INSTANCE_NAME)
    parser.add_argument('--zone', default=ZONE)
    parser.add_argument('--project', default=None)
    parser.add_argument('--archive-script', default=REMOTE_ARCHIVE_SCRIPT)
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
    should_suspend = online and players_online == 0

    check_cmd = gcloud_ssh_command(
        args.instance,
        args.zone,
        'test -f /home/minecraft/cronjobs/usecache_0.json && test -f /home/minecraft/cronjobs/usecache_5.json',
        args.project,
    )
    check_result = run_command(check_cmd, dry_run=False)
    cache_files_ready = check_result.get('ok', False)
    if not cache_files_ready:
        should_suspend = False

    archive_result = None
    cleanup_result = None
    shutdown_result = None
    action = None

    if should_suspend:
        app = create_app()
        with app.app_context():
            # 1. Sync stats to DB first while we have the file
            sync_cache_to_db(args.instance, args.zone, args.project)
            
            # 2. Unban temporary AFKers before stopping
            unban_afk_players(args.instance, args.zone, args.project)
            
            # 3. Shutdown server
            shutdown_result = shutdown_minecraft(args.instance, args.zone, args.project, args.dry_run)
            
            # 4. Archive files
            archive_cmd = gcloud_ssh_command(
                args.instance,
                args.zone,
                f'sudo bash {args.archive_script}',
                args.project,
            )
            archive_result = run_command(archive_cmd, dry_run=args.dry_run)

            if archive_result.get('ok', False):
                cleanup_cmd = gcloud_ssh_command(
                    args.instance,
                    args.zone,
                    'sudo rm -vf /home/minecraft/cronjobs/usecache_*.json',
                    args.project,
                )
                cleanup_result = run_command(cleanup_cmd, dry_run=args.dry_run)

                if cleanup_result.get('ok', False):
                    action = run_gcloud_suspend(args.instance, args.zone, args.project, args.dry_run)

    result = {
        'measured_at': measured_at,
        'status': status,
        'online': online,
        'players_online': players_online,
        'should_suspend': should_suspend,
        'cache_files_ready': cache_files_ready,
        'cache_check': check_result,
        'instance': args.instance,
        'zone': args.zone,
        'project': args.project,
        'archive_script': args.archive_script,
        'archive': archive_result,
        'cleanup': cleanup_result,
        'action': action,
    }
    save_json(Path(args.state_file), result)

    if args.summary:
        print(json.dumps(result))
    else:
        print(json.dumps(result, indent=2, sort_keys=True))

    if any(step and not step.get('ok', False) for step in [shutdown_result, archive_result, cleanup_result, action]):
        sys.exit(1)


if __name__ == '__main__':
    main()
