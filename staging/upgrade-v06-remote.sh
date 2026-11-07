#!/usr/bin/env bash
# In-place, rootless v0.6 update; never touch Bitcoin, PM2, Docker or system dirs.
set -Eeuo pipefail
umask 077
STAGE='/home/electrumbtc1/.swizzle-stage'
APP="$STAGE/app"; EXPECTED="${1:-}"
[[ "$(id -un)" == electrumbtc1 && "$(id -u)" != 0 && "$HOME" == '/home/electrumbtc1' ]] || { echo 'REFUSE: staging owner required';exit 70; }
[[ "$EXPECTED" =~ ^[0-9a-f]{40}$ ]] || { echo 'REFUSE: expected commit SHA missing';exit 71; }
[[ ! -L "$STAGE" && -d "$STAGE" && "$(stat -c %u "$STAGE")" == "$(id -u)" ]] || { echo 'REFUSE: staging ownership invalid';exit 72; }
[[ "$(cat "$STAGE/.swizzle-stage.marker" 2>/dev/null || true)" == 'swizzle-rootless-stage-v03' ]] || { echo 'REFUSE: install marker invalid';exit 73; }
for path in "$APP" "$STAGE/environment" "$STAGE/run" "$STAGE/data" "$STAGE/private";do
 [[ -d "$path" && ! -L "$path" && "$(stat -c %u "$path")" == "$(id -u)" ]] || { echo "REFUSE: invalid staging path $path";exit 74; }
done
[[ -f "$APP/.env" && ! -L "$APP/.env" && "$(stat -c %u "$APP/.env")" == "$(id -u)" ]] || { echo 'REFUSE: stage .env invalid';exit 75; }
[[ "$(git -C "$APP" remote get-url origin)" == 'https://github.com/sumcoinlabs/swizzle.git' ]] || { echo 'REFUSE: unexpected origin';exit 76; }
[[ "$(git -C "$APP" rev-parse HEAD)" == 'b49d117cb0a047dde9289b6af71cdd81699c5ebd' ]] || { echo 'REFUSE: unexpected stage baseline';exit 77; }
[[ -z "$(git -C "$APP" diff --name-only)" && -z "$(git -C "$APP" diff --cached --name-only)" ]] || { echo 'REFUSE: modified tracked staging code';exit 78; }
while IFS= read -r item;do
 case "$item" in accounts/migrations/0*.py|billing/migrations/0*.py|home/migrations/0*.py|newsroom/migrations/0*.py|publishers/migrations/0*.py) :;;
  *) echo "REFUSE: unexpected untracked file $item";exit 79;;
 esac
done < <(git -C "$APP" ls-files --others --exclude-standard)
GUN=$(cat "$STAGE/run/gunicorn.pid")
[[ "$GUN" =~ ^[0-9]+$ && -d "/proc/$GUN" && "$(stat -c %u "/proc/$GUN")" == "$(id -u)" && "$(tr '\0' ' ' < "/proc/$GUN/cmdline")" == *gunicorn* ]] || { echo 'REFUSE: staging gunicorn mismatch';exit 80; }
[[ -x "$STAGE/environment/bin/python" ]] || { echo 'REFUSE: staging Python missing';exit 81; }
if grep -Eq '^GROQ_API_KEY=[^[:space:]]+' "$APP/.env";then
 echo 'REFUSE: key is unexpectedly embedded in .env; fix privately before upgrade';exit 82
fi
printf '\n== VERIFY EXACT NEW COMMIT ==\n'
git -C "$APP" fetch --no-tags --depth 1 origin main
[[ "$(git -C "$APP" rev-parse FETCH_HEAD)" == "$EXPECTED" ]] || { echo 'REFUSE: code changed on GitHub';exit 83; }
git -C "$APP" checkout --detach "$EXPECTED"
[[ -s "$APP/newsroom/dgb_v06/ai_writer.py" && -s "$APP/newsroom/dgb_v06/editorial.py" && -s "$APP/newsroom/dgb_v06/newsroom_v06.py" && -s "$APP/newsroom/dgb_v06/artwork_v06.py" ]] || { echo 'REFUSE: missing pinned DigiByte research modules';exit 84; }
# File path and model are not secret; the key itself is read from mode 0600 user-owned private path.
if ! grep -q '^GROQ_API_KEY_FILE=' "$APP/.env";then printf '\nGROQ_API_KEY_FILE=%s/private/groq.key\n' "$STAGE" >> "$APP/.env";fi
if ! grep -q '^GROQ_MODEL=' "$APP/.env";then printf 'GROQ_MODEL=openai/gpt-oss-120b\n' >> "$APP/.env";fi
if ! grep -q '^NEWSROOM_AUTO_DRAFT=' "$APP/.env";then printf 'NEWSROOM_AUTO_DRAFT=false\n' >> "$APP/.env";fi
cd "$APP";PY="$STAGE/environment/bin/python"
printf '\n== SAFETY AND DATABASE MIGRATION ==\n'
"$PY" - <<'PY'
import os,django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
django.setup()
from django.conf import settings
assert settings.DEBUG and settings.STAGING_DEMO_PAYMENTS
assert not settings.NEWSROOM_AUTO_PUBLISH and not settings.NEWSROOM_AUTO_DRAFT
assert not settings.STRIPE_SECRET_KEY and not settings.STRIPE_WEBHOOK_SECRET
assert not settings.GROQ_API_KEY
assert settings.GROQ_MODEL=='openai/gpt-oss-120b'
print('PASS: no key yet, no payments, no AI auto-drafts or publishing')
PY
"$PY" -m compileall -q newsroom website config publishers accounts billing home
"$PY" manage.py makemigrations newsroom --noinput
"$PY" manage.py migrate --noinput
"$PY" manage.py makemigrations --check --dry-run
"$PY" manage.py check
printf '\n== RUN ALL DJANGO TESTS IN ISOLATED TEST DATABASE ==\n'
"$PY" manage.py test -v 1
"$PY" manage.py collectstatic --noinput --verbosity 0
printf '\n== RELOAD ONLY STAGING WEB PROCESS ==\n'
kill -HUP "$GUN"
sleep 3
[[ -d "/proc/$GUN" && "$(stat -c %u "/proc/$GUN")" == "$(id -u)" ]] || { echo 'FAIL: stage Gunicorn exited';exit 85; }
for url in / /control/ai/;do
 status=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 8 "http://127.0.0.1:8788$url")
 if [[ "$url" == / ]]; then [[ "$status" == 200 ]] || { echo "FAIL: home HTTP $status"; exit 86; }
 else [[ "$status" == 302 ]] || { echo "FAIL: staff page access HTTP $status"; exit 87; };fi
 printf 'PASS %s -> HTTP %s\n' "$url" "$status"
done
printf '\n== RESTART ONLY EXISTING USER-OWNED CELERY WORKER ==\n'
f="$STAGE/run/celery-worker.pid"
if [[ -f "$f" ]];then
 pid=$(cat "$f")
 if [[ -d "/proc/$pid" ]];then
  cmd=$(tr '\0' ' ' < "/proc/$pid/cmdline")
  [[ "$pid" =~ ^[0-9]+$ && "$(stat -c %u "/proc/$pid")" == "$(id -u)" && "$cmd" == *celery* ]] || { echo 'REFUSE: unexpected Celery worker owner/command';exit 88; }
  kill -TERM "$pid"
  for _ in $(seq 1 40);do [[ ! -d "/proc/$pid" ]] && break;sleep .25;done
  if [[ -d "/proc/$pid" ]];then echo 'REFUSE: previous worker did not exit';exit 89;fi
 fi
 rm -f -- "$f"
fi
"$STAGE/environment/bin/celery" -A config.celery:app worker --pool=solo --concurrency=1 --loglevel=WARNING --detach --pidfile="$f" --logfile="$STAGE/logs/celery-worker.log"
sleep 2
[[ -f "$f" ]] || { echo 'FAIL: Celery worker did not start';exit 90; }
pid=$(cat "$f")
[[ -d "/proc/$pid" && "$(stat -c %u "/proc/$pid")" == "$(id -u)" && "$(tr '\0' ' ' < "/proc/$pid/cmdline")" == *celery* ]] || { echo 'FAIL: staging Celery worker mismatch';exit 91; }
printf 'PASS: user-owned Celery worker PID %s\n' "$pid"
printf '\nPASS: v0.6 updated, existing accounts, releases, DB and uninstall preserved.\n'
printf 'Open http://localhost:8988/control/ai/ and install a private key via the provided Mac helper.\n'
