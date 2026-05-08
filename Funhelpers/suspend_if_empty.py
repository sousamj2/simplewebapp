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
REMOTE_ARCHIVE_SCRIPT = '/home/minecraft/cronjobs/archive_cronjobs.sh'


def run_command(cmd, dry_run=False, timeout=120):
    if dry_run:
        return {'ok': True, 'dry_run': True, 'command': cmd, 'stdout': '', 'stderr': ''}
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return {
        'ok': proc.returncode == 0,
        'dry_run': False,
        'command': cmd,
        'stdout': (proc.stdout or '').strip(),
        'stderr': (proc.stderr or '').strip(),
        'returncode': proc.returncode,
    }


def gcloud_ssh_command(instance: str, zone: str, remote_command: str, project: str | None):
    cmd = ['gcloud', 'compute', 'ssh', instance, f'--zone={zone}', f'--command={remote_command}']
    if project:
        cmd.append(f'--project={project}')
    return cmd


def run_gcloud_suspend(instance: str, zone: str, project: str | None, dry_run: bool):
    cmd = ['gcloud', 'compute', 'instances', 'suspend', instance, f'--zone={zone}']
    if project:
        cmd.append(f'--project={project}')
    return run_command(cmd, dry_run=dry_run)


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description='Suspend a GCE VM when the Minecraft server is online with zero players.')
    parser.add_argument('--instance', default=INSTANCE_NAME)
    parser.add_argument('--zone', default=ZONE)
    parser.add_argument('--project', default=None)
    parser.add_argument('--state-file', default=str(STATE_FILE))
    parser.add_argument('--archive-script', default=REMOTE_ARCHIVE_SCRIPT)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--summary', action='store_true')
    args = parser.parse_args()

    measured_at = datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')
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
    action = None

    if should_suspend:
        archive_cmd = gcloud_ssh_command(
            args.instance,
            args.zone,
            f'bash {args.archive_script}',
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

    if any(step and not step.get('ok', False) for step in [archive_result, cleanup_result, action]):
        sys.exit(1)


if __name__ == '__main__':
    main()
