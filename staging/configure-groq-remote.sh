#!/usr/bin/env bash
# Must be invoked with an interactive SSH TTY. Never puts the key in CLI/history/GitHub.
set -Eeuo pipefail
umask 077
STAGE='/home/electrumbtc1/.swizzle-stage'; KEYFILE="$STAGE/private/groq.key"
[[ "$(id -un)" == electrumbtc1 && "$(id -u)" != 0 && "$HOME" == '/home/electrumbtc1' ]] || { echo 'REFUSE: stage account required';exit 70; }
[[ -d "$STAGE" && ! -L "$STAGE" && "$(stat -c %u "$STAGE")" == "$(id -u)" ]] || { echo 'REFUSE: stage owner invalid';exit 71; }
[[ "$(cat "$STAGE/.swizzle-stage.marker")" == swizzle-rootless-stage-v03 ]] || { echo 'REFUSE: stage marker invalid';exit 72; }
[[ -d "$STAGE/private" && ! -L "$STAGE/private" && "$(stat -c %u "$STAGE/private")" == "$(id -u)" ]] || { echo 'REFUSE: private directory invalid';exit 73; }
[[ -f "$STAGE/app/newsroom/research_v06.py" ]] || { echo 'REFUSE: v0.6 code is not installed';exit 74; }
[[ -r /dev/tty ]] || { echo 'REFUSE: use SSH -tt to enter the key without echo';exit 75; }
[[ ! -L "$KEYFILE" ]] || { echo 'REFUSE: key path is a symlink';exit 76; }
if [[ "${1:-}" == '--remove' ]]; then
 rm -f -- "$KEYFILE"
 echo 'Removed only Swizzle private Groq credential.'
else
 printf '\nPaste the new Groq key (hidden; never shown in shell history): ' >/dev/tty
 IFS= read -r -s KEY </dev/tty || { echo 'No key entered' >&2;exit 77; }
 printf '\n' >/dev/tty
 [[ "$KEY" =~ ^gsk_[A-Za-z0-9_-]{20,}$ ]] || { echo 'REFUSE: invalid Groq key format' >&2;unset KEY;exit 78; }
 printf '%s\n' "$KEY" > "$STAGE/private/groq.key.pending"
 chmod 0600 "$STAGE/private/groq.key.pending"
 mv -f -- "$STAGE/private/groq.key.pending" "$KEYFILE"
 unset KEY
 echo 'PASS: key written to owned private file, mode 0600 (key not displayed)'
fi
p="$STAGE/run/gunicorn.pid"
[[ -f "$p" ]] || { echo 'ERROR: web PID missing, no restart';exit 79; }
pid=$(cat "$p")
cmd=$(tr '\0' ' ' < "/proc/$pid/cmdline")
[[ "$pid" =~ ^[0-9]+$ && -d "/proc/$pid" && "$(stat -c %u "/proc/$pid")" == "$(id -u)" && "$cmd" == *gunicorn* ]] || { echo 'REFUSE: gunicorn PID identity mismatch';exit 80; }
kill -HUP "$pid"
printf 'PASS: reloaded only the Swizzle web workers. Next: http://localhost:8988/control/ai/\n'
