#!/usr/bin/env bash
# Actualiza el SGR a una rama, commit o etiqueta y reinicia el servicio.
# Uso (en la EC2):  sudo bash /opt/sgr/app/deploy/actualizar.sh [rama-o-etiqueta] [--datos-demo]
set -euo pipefail
BASE=/opt/sgr
REF="${1:-main}"
APP="$BASE/app"
PY="$BASE/venv/bin/python"
como_sgr() { sudo -u sgr --preserve-env=PATH "$@"; }

cd "$APP"
como_sgr git fetch --all --tags
como_sgr git checkout "$REF"
[ "$(git rev-parse --abbrev-ref HEAD)" != "HEAD" ] && como_sgr git pull --ff-only || true
como_sgr "$BASE/venv/bin/pip" install -r requirements.txt

# sgr/settings.py lee /opt/sgr/app/.env automáticamente.
como_sgr "$PY" manage.py migrate --noinput
como_sgr "$PY" manage.py createcachetable
como_sgr "$PY" manage.py collectstatic --noinput
como_sgr "$PY" manage.py check --deploy || true
if [ "${2:-}" = "--datos-demo" ]; then
  como_sgr "$PY" manage.py cargar_datos_demo
fi

systemctl restart sgr
sleep 2
curl -fsS http://127.0.0.1/salud/ && echo
echo "Versión desplegada: $(git -C "$APP" describe --tags --always)"
