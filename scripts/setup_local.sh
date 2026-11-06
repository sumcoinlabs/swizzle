#!/usr/bin/env bash
# Use ONLY on a Mac/Linux development machine with PostgreSQL running.
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
PYTHON_BIN=${PYTHON_BIN:-python3}
"$PYTHON_BIN" -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if [[ ! -e .env ]]; then
  python - <<'PY'
from pathlib import Path
import secrets
text = Path('.env.example').read_text()
text = text.replace('REPLACE_WITH_RANDOM_SECRET', secrets.token_urlsafe(50))
Path('.env').write_text(text)
print('Created untracked .env with unique development secret')
PY
fi
python manage.py makemigrations home newsroom publishers billing accounts --noinput
python manage.py migrate --noinput
python manage.py bootstrap_site
python manage.py check
python manage.py test
printf '\nLocal development is ready. Create admin with: .venv/bin/python manage.py createsuperuser\n'
printf 'Run: .venv/bin/python manage.py runserver\n'
