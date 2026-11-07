#!/usr/bin/env bash
# Remove ONLY this user's Swizzle staging directory and verified owned child processes.
# Does not use sudo, Docker, PM2, systemctl, apt or any other global resource.
set -Eeuo pipefail
umask 077
STAGE='/home/electrumbtc1/.swizzle-stage'
[[ "$(id -un)" == 'electrumbtc1' && "$(id -u)" != '0' && "$HOME" == '/home/electrumbtc1' ]] || { echo 'REFUSE: uninstall must run as electrumbtc1' >&2; exit 80; }
[[ ! -L "$STAGE" && -d "$STAGE" && "$(stat -c %u "$STAGE")" == "$(id -u)" ]] || { echo 'REFUSE: staging directory missing, linked or wrong owner' >&2; exit 81; }
[[ -f "$STAGE/.swizzle-stage.marker" && ! -L "$STAGE/.swizzle-stage.marker" ]] || { echo 'REFUSE: expected install marker missing' >&2; exit 82; }
[[ "$(cat "$STAGE/.swizzle-stage.marker")" == 'swizzle-rootless-stage-v03' ]] || { echo 'REFUSE: installation marker unexpected' >&2; exit 83; }
# Validate no unexpected symlinks in runtime state, while allowing package symlinks inside env.
for f in "$STAGE/run" "$STAGE/private" "$STAGE/data"; do
 if [[ -e "$f" || -L "$f" ]]; then
  [[ -d "$f" && ! -L "$f" && "$(stat -c %u "$f")" == "$(id -u)" ]] || { echo "REFUSE: unexpected runtime dir $f" >&2; exit 84; }
 fi
done
getcmd() { [[ -r "/proc/$1/cmdline" ]] && tr '\0' ' ' < "/proc/$1/cmdline" || true; }
assert_ours() {
 local pid="$1" name="$2" cmd exe
 [[ "$pid" =~ ^[0-9]+$ && "$pid" -gt 1 ]] || { echo "REFUSE: invalid $name PID" >&2; exit 85; }
 [[ -d "/proc/$pid" ]] || return 1
 [[ "$(stat -c %u "/proc/$pid")" == "$(id -u)" ]] || { echo "REFUSE: $name pid $pid not owned by electrumbtc1" >&2; exit 86; }
 cmd="$(getcmd "$pid")"; exe="$(readlink -f "/proc/$pid/exe" || true)"
 case "$name" in
   postgres) [[ "$cmd" == *"$STAGE/data/postgres"* && "$cmd" == *postgres* ]] || { echo "REFUSE: $pid is not stage postgres: $cmd" >&2; exit 87; };;
   valkey) [[ "$exe" == "$STAGE/environment/"* || "$cmd" == *"$STAGE/private/valkey.conf"* ]] || { echo "REFUSE: $pid is not stage valkey: $cmd" >&2; exit 87; };;
   gunicorn|celery) [[ "$cmd" == *"$STAGE/environment/"* || "$cmd" == *"$STAGE/app"* ]] || { echo "REFUSE: $pid is not stage $name: $cmd" >&2; exit 87; };;
 esac
 return 0
}
stop_pid() {
 local file="$1" name="$2" pid
 [[ -f "$file" && ! -L "$file" ]] || return 0
 pid="$(cat "$file")"
 if ! assert_ours "$pid" "$name"; then printf '%s already stopped\n' "$name";return;fi
 kill -TERM "$pid" || { echo "REFUSE: couldn't stop $name" >&2;exit 88; }
 for _ in $(seq 1 30);do
   if [[ ! -d "/proc/$pid" ]];then break;fi
   sleep 0.3
 done
 if [[ -d "/proc/$pid" ]];then echo "REFUSE: $name PID $pid did not exit" >&2;exit 89;fi
 echo "Stopped $name PID $pid"
}
printf '== VERIFY/STOP ONLY SWIZZLE USER PROCESSES ==\n'
stop_pid "$STAGE/run/celery-beat.pid" celery
stop_pid "$STAGE/run/celery-worker.pid" celery
stop_pid "$STAGE/run/gunicorn.pid" gunicorn
# Validate PG postmaster identity before using its own pg_ctl -D to shut down.
if [[ -f "$STAGE/data/postgres/postmaster.pid" ]];then
 pid=$(head -n1 "$STAGE/data/postgres/postmaster.pid")
 if assert_ours "$pid" postgres;then
  [[ -x "$STAGE/environment/bin/pg_ctl" ]] || { echo 'REFUSE: stage pg_ctl missing' >&2;exit 90; }
  "$STAGE/environment/bin/pg_ctl" -D "$STAGE/data/postgres" -w -m fast stop
 fi
fi
if [[ -f "$STAGE/run/valkey.pid" ]];then
 pid=$(cat "$STAGE/run/valkey.pid")
 if assert_ours "$pid" valkey;then
  [[ -x "$STAGE/environment/bin/python" ]] || { echo 'REFUSE: stage Python missing' >&2;exit 91; }
  "$STAGE/environment/bin/python" - <<'PY'
import redis
from pathlib import Path
p=Path('/home/electrumbtc1/.swizzle-stage')
password=(p/'private/valkey.pass').read_text().strip()
r=redis.Redis(host='127.0.0.1',port=16388,password=password,socket_connect_timeout=3)
r.shutdown(nosave=True)
PY
 fi
fi
# Never delete while ANY process is still using the installed runtimes or database.
python3 - <<'PY'
import os
from pathlib import Path
prefix='/home/electrumbtc1/.swizzle-stage/'
myuid=os.getuid()
for proc in Path('/proc').iterdir():
 if not proc.name.isdecimal():continue
 try:
  pid=int(proc.name)
  if pid == os.getpid():continue
  cmd=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode('utf8','replace')
  exe=str((proc/'exe').resolve())
 except (OSError,PermissionError,ProcessLookupError):continue
 if (prefix+'environment/' in cmd or prefix+'data/postgres' in cmd or exe.startswith(prefix+'environment/')):
  raise SystemExit('REFUSE: process still using staging (UID %s): pid %s cmd %.200s' %(os.stat(proc).st_uid,pid,cmd))
print('PASS: no active staging runtime processes found')
PY
# Double-check the exact path before removal (no wildcards).
[[ "$STAGE" == '/home/electrumbtc1/.swizzle-stage' && "$(cat "$STAGE/.swizzle-stage.marker")" == 'swizzle-rootless-stage-v03' ]] || exit 92
rm -rf -- "$STAGE"
[[ ! -e "$STAGE" ]] || { echo 'REFUSE: cleanup incomplete' >&2;exit 93; }
printf '\nPASS: Swizzle staging entirely removed from this user home.\n'
printf 'Nothing in /root, /etc, /usr, Docker, systemd or PM2 was modified.\n'
