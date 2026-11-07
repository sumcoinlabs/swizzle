#!/usr/bin/env bash
# Existing rootless stage, exact SHA, in-place extension. Never root/sudo/PM2/Docker/Bitcoin.
set -Eeuo pipefail
umask 077
EXPECTED_SHA="${1:-}"
STAGE='/home/electrumbtc1/.swizzle-stage'
APP="$STAGE/app"
[[ "$(id -un)" == 'electrumbtc1' && "$(id -u)" != '0' && "$HOME" == '/home/electrumbtc1' ]] || { echo 'REFUSE: expected electrumbtc1, not root' >&2;exit 70; }
[[ "$EXPECTED_SHA" =~ ^[0-9a-f]{40}$ ]] || { echo 'REFUSE: invalid expected SHA' >&2;exit 71; }
[[ ! -L "$STAGE" && -d "$STAGE" && "$(stat -c %u "$STAGE")" == "$(id -u)" ]] || { echo 'REFUSE: staging directory invalid' >&2;exit 72; }
[[ -f "$STAGE/.swizzle-stage.marker" && "$(cat "$STAGE/.swizzle-stage.marker")" == 'swizzle-rootless-stage-v03' ]] || { echo 'REFUSE: unexpected staging install marker' >&2;exit 73; }
for item in "$APP" "$STAGE/environment" "$STAGE/run" "$STAGE/data" "$STAGE/private"; do
 [[ -d "$item" && ! -L "$item" && "$(stat -c %u "$item")" == "$(id -u)" ]] || { echo "REFUSE: unsafe stage directory: $item" >&2;exit 74; }
done
[[ -f "$APP/.env" && ! -L "$APP/.env" && "$(stat -c %u "$APP/.env")" == "$(id -u)" ]] || { echo 'REFUSE: unexpected stage env' >&2;exit 75; }
[[ -x "$STAGE/environment/bin/python" ]] || { echo 'REFUSE: missing stage Python' >&2;exit 76; }
[[ "$(git -C "$APP" remote get-url origin)" == 'https://github.com/sumcoinlabs/swizzle.git' ]] || { echo 'REFUSE: unexpected Git repo' >&2;exit 77; }
[[ -z "$(git -C "$APP" diff --name-only)" && -z "$(git -C "$APP" diff --cached --name-only)" ]] || { echo 'REFUSE: modified tracked stage code' >&2;exit 78; }
while IFS= read -r untracked; do
 case "$untracked" in accounts/migrations/0*.py|billing/migrations/0*.py|home/migrations/0*.py|newsroom/migrations/0*.py|publishers/migrations/0*.py) ;;
 *) echo "REFUSE: unexpected untracked path $untracked" >&2;exit 79;;
 esac
done < <(git -C "$APP" ls-files --others --exclude-standard)
GUNICORN_PID=$(cat "$STAGE/run/gunicorn.pid")
[[ "$GUNICORN_PID" =~ ^[0-9]+$ && "$GUNICORN_PID" -gt 1 && -d "/proc/$GUNICORN_PID" ]] || { echo 'REFUSE: missing stage Gunicorn PID' >&2;exit 80; }
[[ "$(stat -c %u "/proc/$GUNICORN_PID")" == "$(id -u)" && "$(tr '\0' ' ' < "/proc/$GUNICORN_PID/cmdline")" == *gunicorn* ]] || { echo 'REFUSE: Gunicorn does not belong to stage account' >&2;exit 81; }
[[ "$(git -C "$APP" rev-parse HEAD)" == 'cf20d8aff6819779efea8653143fb73bea8c9a32' ]] || { echo 'REFUSE: unexpected deployed baseline; no stage edits attempted' >&2;exit 82; }
printf '\n== FETCH APPROVED V0.5 SOURCE (NO EXTRA HOST CHANGES) ==\n'
git -C "$APP" fetch --no-tags --depth 1 origin main
[[ "$(git -C "$APP" rev-parse FETCH_HEAD)" == "$EXPECTED_SHA" ]] || { echo 'REFUSE: exact SHA mismatch' >&2;exit 83; }
git -C "$APP" checkout --detach "$EXPECTED_SHA"
PY="$STAGE/environment/bin/python"
cd "$APP"
printf '\n== VERIFY STAGING SAFETY AND APPLY ONE MODEL MIGRATION ==\n'
if ! grep -q '^STAGING_DEMO_PAYMENTS=' .env;then printf '\nSTAGING_DEMO_PAYMENTS=true\n' >> .env;fi
"$PY" - <<'PY'
import os,django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
django.setup()
from django.conf import settings
assert settings.DEBUG and not settings.NEWSROOM_AUTO_PUBLISH and settings.STAGING_DEMO_PAYMENTS, 'REFUSE: staging safety settings are not satisfied'
assert not settings.STRIPE_SECRET_KEY and not settings.STRIPE_WEBHOOK_SECRET, 'REFUSE: Stripe credentials must not be present in staging demo'
assert not settings.GROQ_API_KEY, 'REFUSE: this initial v0.5 stage update must not inherit an AI key'
print('PASS: DEBUG staging, mock payment enabled, Stripe and auto-publishing disabled')
PY
"$PY" -m compileall -q config website home publishers newsroom accounts billing
"$PY" manage.py makemigrations publishers --noinput
"$PY" manage.py migrate --noinput
"$PY" manage.py makemigrations --check --dry-run
"$PY" manage.py check
printf '\n== DJANGO END-TO-END TESTS (ISOLATED TEST DB) ==\n'
"$PY" manage.py test -v 1
printf '\n== ENABLE THREE OFFICIAL RELEASE SOURCES ONLY ==\n'
"$PY" manage.py enable_staging_sources
"$PY" manage.py collectstatic --noinput --verbosity 0
printf '\n== RELOAD ONLY OUR USER-OWNED GUNICORN ==\n'
kill -HUP "$GUNICORN_PID"
sleep 3
[[ -d "/proc/$GUNICORN_PID" && "$(stat -c %u "/proc/$GUNICORN_PID")" == "$(id -u)" ]] || { echo 'FAIL: stage Gunicorn exited' >&2;exit 84; }
for url in / /control/ /control/sources/ /control/leads/ /control/releases/ /control/companies/;do
 status=$(curl -sS --max-time 8 -o /dev/null -w '%{http_code}' "http://127.0.0.1:8788$url")
 if [[ "$url" == '/' ]];then [[ "$status" == 200 ]] || { echo "FAIL: homepage status $status" >&2;exit 85; };else [[ "$status" == 302 ]] || { echo "FAIL: $url access protection status $status" >&2;exit 86; };fi
 echo "PASS $url HTTP $status"
done
printf '\n== START OPTIONAL USER-OWNED SCHEDULED FEED WORKERS ==\n'
# Celery's task limit is zero for AI in this staging env. Source polling is allowed.
if [[ ! -f "$STAGE/run/celery-worker.pid" ]]; then
 "$STAGE/environment/bin/celery" -A config.celery:app worker --pool=solo --concurrency=1 --loglevel=WARNING --detach --pidfile="$STAGE/run/celery-worker.pid" --logfile="$STAGE/logs/celery-worker.log"
fi
if [[ ! -f "$STAGE/run/celery-beat.pid" ]]; then
 "$STAGE/environment/bin/celery" -A config.celery:app beat --loglevel=WARNING --detach --pidfile="$STAGE/run/celery-beat.pid" --logfile="$STAGE/logs/celery-beat.log" --schedule="$STAGE/data/celerybeat-schedule"
fi
sleep 3
for name in celery-worker celery-beat;do
 f="$STAGE/run/$name.pid"
 if [[ -f "$f" ]];then
  pid=$(cat "$f"); cmd=$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)
  [[ "$pid" =~ ^[0-9]+$ && -d "/proc/$pid" && "$(stat -c %u "/proc/$pid")" == "$(id -u)" && "$cmd" == *celery* ]] || { echo "FAIL: $name PID ownership mismatch" >&2;exit 87; }
  echo "PASS $name PID $pid belongs to electrumbtc1"
 else
  echo "WARN: $name did not produce a PID file; check $STAGE/logs" >&2
 fi
done
printf '\nPASS: v0.5 installed as electrumbtc1, PostgreSQL and user data preserved.\n'
printf 'Open http://localhost:8988/control/\n'
printf 'Original removal command remains: bash ~/Downloads/swizzle-rootless-v03/staging/remove-from-mac.sh\n'
