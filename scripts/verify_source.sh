#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
python3 -m compileall -q config home newsroom publishers billing accounts website
if grep -R -E '^\s*DJANGO_SECRET_KEY\s*=\s*[^#\s]' . --include='*.py' | grep -v 'os.getenv'; then
  echo 'Review hardcoded credential matches above' >&2; exit 1
fi
printf 'PASS: Python files compile and no obvious hardcoded Django key\n'
