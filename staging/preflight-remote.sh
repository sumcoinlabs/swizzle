#!/usr/bin/env bash
# Read-only check. Executes remotely as electrumbtc1. Makes NO changes.
set -Eeuo pipefail
[[ "$(id -un)" == 'electrumbtc1' ]] || { echo 'REFUSE: SSH session is not electrumbtc1' >&2; exit 60; }
[[ "$(id -u)" != '0' ]] || { echo 'REFUSE: root session' >&2; exit 61; }
[[ "$(uname -s)" == 'Linux' && "$(uname -m)" == 'x86_64' ]] || { echo 'REFUSE: only Linux x86_64 supported' >&2; exit 62; }
[[ "$HOME" == "$(getent passwd electrumbtc1 | cut -d: -f6)" ]] || { echo 'REFUSE: unexpected HOME' >&2; exit 63; }
[[ ! -L "$HOME" && "$HOME" == '/home/electrumbtc1' ]] || { echo 'REFUSE: unusual home directory' >&2; exit 64; }
[[ ! -e "$HOME/.swizzle-stage" && ! -L "$HOME/.swizzle-stage" ]] || { echo 'REFUSE: staging path already exists; inspect it before proceeding' >&2; exit 65; }
for x in curl tar git bzip2 python3 ss df getent ps; do command -v "$x" >/dev/null || { echo "REFUSE: missing $x" >&2; exit 66; }; done
printf '\n== SWIZZLE ROOTLESS PREFLIGHT (READ ONLY) ==\n'
whoami; cat /etc/os-release | grep -E '^PRETTY_NAME=' || true
python3 - <<'PY'
import socket
for port in (8788, 15488, 16388):
    s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    try:
        s.bind(('127.0.0.1',port))
        print('PASS: 127.0.0.1:%s is unoccupied at preflight' % port)
    except OSError as exc:
        raise SystemExit('REFUSE: port %s cannot be bound: %s' % (port,exc))
    finally:
        s.close()
PY
free=$(df -Pk "$HOME" | awk 'NR==2{print $4}')
[[ "$free" =~ ^[0-9]+$ && "$free" -ge 4194304 ]] || { echo 'REFUSE: less than 4 GiB free on HOME filesystem' >&2; exit 67; }
printf 'PASS: free disk >= 4 GiB; stage will stay in %s\n' "$HOME/.swizzle-stage"
printf 'PASS: no sudo, system installation, PM2 changes or Docker usage needed\n'
