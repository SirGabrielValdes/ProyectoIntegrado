#!/usr/bin/env bash
# Actualiza el SGR instalado con instalar_ec2.sh y reinicia el servicio.
# Uso (en la EC2):  sudo bash /opt/sgr/app/deploy/actualizar.sh [rama|commit|etiqueta] [--datos-demo]
# Sin argumentos trae los últimos cambios de la rama actual.
set -euo pipefail
BASE=/opt/sgr
APP="$BASE/app"
PY="$BASE/venv/bin/python"
cd "$APP"
REF="${1:-$(sudo -u sgr git rev-parse --abbrev-ref HEAD)}"

sudo -u sgr git fetch -q --all --tags
sudo -u sgr git checkout -q "$REF"
if [ "$(sudo -u sgr git rev-parse --abbrev-ref HEAD)" != "HEAD" ]; then sudo -u sgr git pull -q --ff-only; fi
sudo -u sgr "$BASE/venv/bin/pip" install -q -r requirements.txt

# sgr/settings.py lee /opt/sgr/app/.env automáticamente.
sudo -u sgr "$PY" manage.py migrate --noinput
sudo -u sgr "$PY" manage.py collectstatic --noinput -v0
if [ "${2:-}" = "--datos-demo" ]; then sudo -u sgr "$PY" manage.py cargar_datos_demo; fi

if [ -d /run/systemd/system ]; then
  systemctl restart sgr
else
  pkill -f "gunicorn sgr.wsgi" || true
  sudo -u sgr nohup "$BASE/venv/bin/gunicorn" sgr.wsgi:application -c deploy/gunicorn.conf.py > "$BASE/gunicorn.log" 2>&1 &
fi
for i in $(seq 1 30); do curl -fs -o /dev/null http://127.0.0.1/salud/ && break; sleep 1; done
curl -fsS http://127.0.0.1/salud/ && echo
echo "Versión desplegada: $(sudo -u sgr git describe --tags --always)"
