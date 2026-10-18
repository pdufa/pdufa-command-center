#!/usr/bin/env bash
# Installs ONLY new-platform docker services. Does not run Streamlit commands.
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required. Install Docker Desktop or Docker Engine first." >&2
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose v2 is required." >&2
  exit 1
fi

if [ ! -f .env ]; then
  python3 - <<'PY'
import os
import pathlib
import secrets
path = pathlib.Path(".env")
values = {
    "POSTGRES_PASSWORD": secrets.token_hex(24),
    "PDUFA_INTERNAL_API_KEY": secrets.token_hex(32),
    "DASHBOARD_PASSWORD": secrets.token_urlsafe(24),
    "SESSION_SIGNING_KEY": secrets.token_hex(32),
}
with path.open("x") as handle:
    for name, value in values.items():
        handle.write(name + "=" + value + "\n")
os.chmod(path, 0o600)
print("Created private .env file with unique random local setup secrets.")
print("New dashboard password: " + values["DASHBOARD_PASSWORD"])
print("Keep this password private; later view it securely from .env if needed.")
PY
else
  echo "Using existing new-platform/.env; secrets were not changed."
fi

docker compose up --build -d
docker compose ps
echo "New platform test URL (on this machine): http://127.0.0.1:3000"
echo "Streamlit production services were not modified."
