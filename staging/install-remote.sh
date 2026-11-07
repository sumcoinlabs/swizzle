#!/usr/bin/env bash
# Rootless, single-user, removable staging installation of Swizzle.
# Must be executed by electrumbtc1 over SSH. No sudo, Docker or system services.
set -Eeuo pipefail
umask 077
NAME='electrumbtc1'; STAGE='/home/electrumbtc1/.swizzle-stage'; URL='https://github.com/sumcoinlabs/swizzle.git'
EXPECTED_SHA="${SWIZZLE_EXPECTED_SHA:-}"
[[ "$(id -un)" == "$NAME" && "$(id -u)" != '0' && "$HOME" == '/home/electrumbtc1' ]] || { echo 'REFUSE: must run as electrumbtc1, never root' >&2; exit 70; }
[[ "$EXPECTED_SHA" =~ ^[0-9a-f]{40}$ ]] || { echo 'REFUSE: expected git commit SHA is required' >&2; exit 71; }
[[ ! -e "$STAGE" && ! -L "$STAGE" ]] || { echo 'REFUSE: stage already exists; use uninstall or inspect first' >&2; exit 72; }
# Recheck rootless prerequisite and port bindings immediately before any writes.
python3 - <<'PY'
import socket
for port in (8788,15488,16388):
 s=socket.socket()
 try:s.bind(('127.0.0.1',port))
 except OSError as e:raise SystemExit('REFUSE port %s: %s' % (port,e))
 finally:s.close()
PY
mkdir -m 0700 "$STAGE"; printf 'swizzle-rootless-stage-v03\n' > "$STAGE/.swizzle-stage.marker"
mkdir -m 0700 "$STAGE"/{tools,run,logs,private,data,mamba-root} "$STAGE/run/pg"
printf '\n== DOWNLOAD SWIZZLE REPOSITORY (EXACT REVIEWED COMMIT) ==\n'
git clone --depth 1 --branch main "$URL" "$STAGE/app"
cd "$STAGE/app"
ACTUAL_SHA=$(git rev-parse HEAD)
[[ "$ACTUAL_SHA" == "$EXPECTED_SHA" ]] || { echo "REFUSE: GitHub commit changed ($ACTUAL_SHA != $EXPECTED_SHA)" >&2; exit 73; }
printf 'Swizzle source commit: %s\n' "$ACTUAL_SHA"
printf '\n== ROOTLESS MICROMAMBA (OWNED BY USER) ==\n'
mkdir -m 0700 "$STAGE/tools/bin"
curl --fail --location --silent --show-error --retry 2 'https://micro.mamba.pm/api/micromamba/linux-64/latest' | tar -xj -C "$STAGE/tools" bin/micromamba
[[ -x "$STAGE/tools/bin/micromamba" ]] || { echo 'micromamba extraction failed' >&2; exit 74; }
export MAMBA_ROOT_PREFIX="$STAGE/mamba-root"
export CONDA_PKGS_DIRS="$STAGE/mamba-root/pkgs"
export CONDARC="$STAGE/private/.condarc"
printf "channels:\n  - conda-forge\nchannel_priority: strict\n" > "$CONDARC"
"$STAGE/tools/bin/micromamba" create --yes --prefix "$STAGE/environment" --override-channels -c conda-forge 'python=3.13' 'postgresql=16.*' 'valkey-server=9.*' pip
export PATH="$STAGE/environment/bin:$PATH"
PY="$STAGE/environment/bin/python"
for tool in "$PY" "$STAGE/environment/bin/initdb" "$STAGE/environment/bin/pg_ctl" "$STAGE/environment/bin/createdb" "$STAGE/environment/bin/valkey-server"; do
 [[ -x "$tool" ]] || { echo "Missing runtime executable: $tool" >&2; exit 75; }
done
printf '\n== INSTALL PYTHON DEPENDENCIES ==\n'
"$PY" -m pip install --disable-pip-version-check --no-input -r "$STAGE/app/requirements.txt"
printf '\n== PRIVATE POSTGRESQL AND VALKEY CREDENTIALS ==\n'
"$PY" - <<'PY'
import pathlib,secrets
p=pathlib.Path('/home/electrumbtc1/.swizzle-stage/private')
for n in ('pg.pass','valkey.pass','django.secret'):
 f=p/n; f.write_text(secrets.token_urlsafe(40)+'\n'); f.chmod(0o600)
PY
PGPASSWORD="$(cat "$STAGE/private/pg.pass")"; export PGPASSWORD
"$STAGE/environment/bin/initdb" -D "$STAGE/data/postgres" --username=swizzle_stage --auth-local=scram-sha-256 --auth-host=scram-sha-256 --pwfile="$STAGE/private/pg.pass" --no-instructions >/dev/null
"$STAGE/environment/bin/pg_ctl" -D "$STAGE/data/postgres" -l "$STAGE/logs/postgresql.log" -o "-c listen_addresses=127.0.0.1 -c port=15488 -c unix_socket_directories=$STAGE/run/pg -c unix_socket_permissions=0700" -w start
"$STAGE/environment/bin/createdb" -h 127.0.0.1 -p 15488 -U swizzle_stage swizzle_stage
unset PGPASSWORD
"$PY" - <<'PY'
from pathlib import Path
p=Path('/home/electrumbtc1/.swizzle-stage')
secret=lambda name:(p/'private'/name).read_text().strip()
conf=(f'bind 127.0.0.1\nport 16388\nprotected-mode yes\nrequirepass {secret("valkey.pass")}\n'
      f'dir {p}/data\npidfile {p}/run/valkey.pid\nlogfile {p}/logs/valkey.log\n'
      'daemonize yes\nsave ""\nappendonly no\nmaxmemory 256mb\nmaxmemory-policy noeviction\n')
c=p/'private'/'valkey.conf';c.write_text(conf);c.chmod(0o600)
from urllib.parse import quote
pg=quote(secret('pg.pass'),safe='');vk=quote(secret('valkey.pass'),safe='')
lines={
 'DJANGO_SECRET_KEY':secret('django.secret'), 'DJANGO_DEBUG':'true',
 'DJANGO_ALLOWED_HOSTS':'localhost,127.0.0.1',
 'CSRF_TRUSTED_ORIGINS':'http://localhost:8988,http://127.0.0.1:8988',
 'SITE_NAME':'Swizzle Staging', 'SITE_DOMAIN':'localhost', 'SITE_TAGLINE':'News and publisher preview',
 'DATABASE_URL':f'postgresql://swizzle_stage:{pg}@127.0.0.1:15488/swizzle_stage',
 'CELERY_BROKER_URL':f'redis://:{vk}@127.0.0.1:16388/0',
 'CELERY_RESULT_BACKEND':f'redis://:{vk}@127.0.0.1:16388/1',
 'NEWSROOM_AUTO_PUBLISH':'false', 'NEWSROOM_ITEMS_PER_RUN':'0',
 'GROQ_API_KEY':'', 'STRIPE_SECRET_KEY':'', 'STRIPE_WEBHOOK_SECRET':'',
 'STRIPE_READER_MONTHLY_PRICE_ID':'', 'TURNSTILE_SITE_KEY':'', 'TURNSTILE_SECRET_KEY':'',
 'ADSENSE_CLIENT_ID':'','ADSENSE_SLOT_ID':'',
 'WAGTAILADMIN_BASE_URL':'http://localhost:8988'
}
f=p/'app'/'.env'; f.write_text(''.join(f'{k}={v}\n' for k,v in lines.items()));f.chmod(0o600)
PY
"$STAGE/environment/bin/valkey-server" "$STAGE/private/valkey.conf"
"$PY" - <<'PY'
from pathlib import Path
import redis
p=Path('/home/electrumbtc1/.swizzle-stage')
r=redis.Redis(host='127.0.0.1',port=16388,password=(p/'private/valkey.pass').read_text().strip())
assert r.ping(), 'Valkey did not start'
print('PASS: private Valkey running on 127.0.0.1:16388')
PY
printf '\n== MIGRATE AND VERIFY DJANGO ==\n'
cd "$STAGE/app"
"$PY" manage.py makemigrations home newsroom publishers billing accounts --noinput
"$PY" manage.py migrate --noinput
"$PY" manage.py bootstrap_site
# Public DigiByte newsroom source catalog: import inactive only; never touch the DigiByte VM.
if curl --fail --location --silent --show-error --retry 1 https://raw.githubusercontent.com/sumcoinlabs/dgb-newsroom-engine/main/sources.json -o "$STAGE/data/dgb-sources.json"; then
  "$PY" manage.py import_dgb_sources "$STAGE/data/dgb-sources.json"
else
  echo "WARN: DigiByte public RSS sources unavailable; stage remains usable" >&2
fi
"$PY" manage.py shell -c 'from wagtail.models import Site; Site.objects.filter(is_default_site=True).update(port=8988)'
"$PY" manage.py check
"$PY" manage.py collectstatic --noinput --verbosity 0
"$PY" manage.py test --verbosity 1
printf '\n== CREATE STAGING ADMIN (CREDENTIALS ON SERVER ONLY) ==\n'
"$PY" - <<'PY'
import os,sys,secrets
from pathlib import Path
p=Path('/home/electrumbtc1/.swizzle-stage')
sys.path.insert(0,str(p/'app'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django
django.setup()
from django.contrib.auth import get_user_model
password=secrets.token_urlsafe(20)
U=get_user_model()
if not U.objects.filter(username='stageadmin').exists():
 U.objects.create_superuser(username='stageadmin', email='', password=password)
 f=p/'private'/'admin-login.txt'; f.write_text('username: stageadmin\npassword: '+password+'\n');f.chmod(0o600)
PY
printf '\n== START WEB (LOOPBACK ONLY) ==\n'
"$STAGE/environment/bin/gunicorn" config.wsgi:application --chdir "$STAGE/app" --bind 127.0.0.1:8788 --workers 2 --daemon --pid "$STAGE/run/gunicorn.pid" --error-logfile "$STAGE/logs/gunicorn-error.log" --access-logfile "$STAGE/logs/gunicorn-access.log"
python3 - <<'PY'
import time,urllib.request
url='http://127.0.0.1:8788/'
for attempt in range(25):
 try:
  with urllib.request.urlopen(url,timeout=3) as response:
   if response.status < 500:
    print('PASS: Swizzle staging HTTP',response.status);break
 except Exception:
  time.sleep(1)
else:raise SystemExit('REFUSE: HTTP health test failed; inspect logs and uninstall')
PY
printf '\n== VERIFY ALL SERVICES ARE OWNED BY ELECTRUMBTC1 ==\n'
python3 - <<'PY'
from pathlib import Path
import os
p=Path('/home/electrumbtc1/.swizzle-stage/run')
for name in ('gunicorn.pid','valkey.pid'):
 f=p/name
 pid=int(f.read_text().strip())
 owner=os.stat('/proc/'+str(pid)).st_uid
 if owner != os.getuid():raise SystemExit(f'REFUSE {name}: pid {pid} owned by UID {owner}')
 print('PASS',name,'PID',pid,'UID',owner)
p=Path('/home/electrumbtc1/.swizzle-stage/data/postgres/postmaster.pid')
pid=int(p.read_text().splitlines()[0])
owner=os.stat('/proc/'+str(pid)).st_uid
if owner!=os.getuid():raise SystemExit(f'REFUSE postgres pid {pid} owned by UID {owner}')
print('PASS postgresql PID',pid,'UID',owner)
PY
printf '\n== READY ==\n'
printf 'Swizzle is reachable ONLY via SSH tunnel:\n'
printf 'ssh -N -L 8988:127.0.0.1:8788 electrumbtc1@159.118.235.181\n'
printf 'Website: http://localhost:8988/\nAdmin: http://localhost:8988/admin/\n'
printf 'To see admin login securely: ssh electrumbtc1@159.118.235.181 "cat ~/.swizzle-stage/private/admin-login.txt"\n'
printf 'To uninstall: bash ~/.swizzle-stage/app/staging/uninstall-remote.sh\n'
printf 'NOTE: This is a staging preview, not a production HTTPS deployment. No payments or public automation enabled.\n'
