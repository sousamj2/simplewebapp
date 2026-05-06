#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from mc_server_status import get_mc_status

STATE_FILE = Path('/var/www/appmodules/simplewebapp/scripts/suspend_if_empty_state.json')
INSTANCE_NAME = 'mcserver-mem8'
ZONE = 'europe-west1-b'


def run_gcloud_suspend(instance: str, zone: str, project: str | None, dry_run: bool):
    cmd = ['gcloud', 'compute', 'instances', 'suspend', instance, f'--zone={zone}']
    if project:
        cmd.append(f'--project={project}')
    if dry_run:
        return {'ok': True, 'dry_run': True, 'command': cmd, 'stdout': '', 'stderr': ''}
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return {
        'ok': proc.returncode == 0,
        'dry_run': False,
        'command': cmd,
        'stdout': (proc.stdout or '').strip(),
        'stderr': (proc.stderr or '').strip(),
        'returncode': proc.returncode,
    }


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description='Suspend a GCE VM when the Minecraft server is online with zero players.')
    parser.add_argument('--instance', default=INSTANCE_NAME)
    parser.add_argument('--zone', default=ZONE)
    parser.add_argument('--project', default=None)
    parser.add_argument('--state-file', default=str(STATE_FILE))
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--summary', action='store_true')
    args = parser.parse_args()

    measured_at = datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')
    status = get_mc_status()
    online = bool(status.get('online'))
    players_online = int(status.get('players_online', 0) or 0)
    should_suspend = online and players_online == 0
    action = None
    cleanup = None

    if should_suspend:
        cleanup_cmd = [
            'gcloud', 'compute', 'ssh', args.instance,
            f'--zone={args.zone}',
            "--command=sudo rm -vf /home/minecraft/cronjobs/usecache_*.json",
        ]
        if args.project:
            cleanup_cmd.append(f'--project={args.project}')

        if args.dry_run:
            cleanup = {'ok': True, 'dry_run': True, 'command': cleanup_cmd}
        else:
            cleanup_proc = subprocess.run(cleanup_cmd, capture_output=True, text=True, timeout=120)
            cleanup = {
                'ok': cleanup_proc.returncode == 0,
                'dry_run': False,
                'command': cleanup_cmd,
                'stdout': (cleanup_proc.stdout or '').strip(),
                'stderr': (cleanup_proc.stderr or '').strip(),
                'returncode': cleanup_proc.returncode,
            }

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
        'action': action,
    }
    save_json(Path(args.state_file), result)

    if args.summary:
        print(json.dumps(result))
    else:
        print(json.dumps(result, indent=2, sort_keys=True))

    if action and not action.get('ok', False):
        sys.exit(1)


if __name__ == '__main__':
    main()
