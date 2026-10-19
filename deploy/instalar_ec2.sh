#!/usr/bin/env bash
# =============================================================================
# SGR · Instalación completa en una instancia AWS EC2 (Ubuntu 22.04 / 24.04)
#
# En la EC2:
#   git clone https://github.com/SirGabrielValdes/ProyectoIntegrado.git
#   cd ProyectoIntegrado
#   sudo bash deploy/instalar_ec2.sh
#
# Hace todo: paquetes, base de datos MariaDB local, entorno Python, archivo .env
# con claves aleatorias, IP pública, correo de recuperación (Gmail opcional),
# datos de prueba, gunicorn + nginx y verificación final.
# Puede ejecutarse de nuevo sin perder la configuración (.env se conserva).
#
# Preguntas evitables con variables de entorno (instalación desatendida):
#   SGR_CORREO_ADMIN   correo personal que recibirá el código del superadmin
#   SGR_GMAIL          cuenta Gmail que envía los correos
#   SGR_GMAIL_CLAVE    "contraseña de aplicación" de esa cuenta Gmail
#   SGR_CLAVE_DEMO     clave de los usuarios de prueba (si no, se genera una)
# =============================================================================
set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "Ejecute con sudo: sudo bash deploy/instalar_ec2.sh"; exit 1; }

ORIGEN="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="${SGR_REPO:-$(git -C "$ORIGEN" remote get-url origin 2>/dev/null || echo https://github.com/SirGabrielValdes/ProyectoIntegrado.git)}"
REF="${SGR_REF:-$(git -C "$ORIGEN" rev-parse --abbrev-ref HEAD 2>/dev/null || echo HEAD)}"
[ "$REF" = "HEAD" ] && REF="$(git -C "$ORIGEN" rev-parse HEAD)"
BASE=/opt/sgr
APP="$BASE/app"
ENVF="$APP/.env"

paso() { echo; echo "==> $*"; }
preguntar() {  # preguntar VAR "texto" [oculto]
  local var="$1" texto="$2" oculto="${3:-}" valor=""
  if [ -n "${!var:-}" ]; then return; fi
  if [ -r /dev/tty ]; then
    if [ -n "$oculto" ]; then read -r -s -p "$texto" valor < /dev/tty; echo; else read -r -p "$texto" valor < /dev/tty; fi
  fi
  printf -v "$var" '%s' "$valor"
}
aleatorio() { python3 -c "import secrets,sys; print(secrets.token_urlsafe(int(sys.argv[1])))" "$1"; }
con_systemd() { [ -d /run/systemd/system ]; }
servicio() {  # servicio <accion> <nombre>
  if con_systemd; then systemctl "$1" "$2"; else service "$2" "$1" >/dev/null 2>&1 || true; fi
}

# -----------------------------------------------------------------------------
paso "Paquetes del sistema"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y -q
apt-get install -y -q python3 python3-venv python3-pip git nginx mariadb-server curl
if con_systemd; then systemctl enable --now mariadb; else service mariadb start || true; fi

paso "Usuario de servicio y código ($REF)"
id sgr >/dev/null 2>&1 || useradd --system --create-home --shell /usr/sbin/nologin --gid www-data sgr
mkdir -p "$BASE"; chown sgr:www-data "$BASE"
if [ ! -d "$APP/.git" ]; then
  sudo -u sgr git clone -q "$REPO" "$APP"
fi
sudo -u sgr git -C "$APP" fetch -q --all --tags
sudo -u sgr git -C "$APP" checkout -q "$REF"
if [ "$(sudo -u sgr git -C "$APP" rev-parse --abbrev-ref HEAD)" != "HEAD" ]; then sudo -u sgr git -C "$APP" pull -q --ff-only; fi

paso "Entorno Python"
[ -d "$BASE/venv" ] || sudo -u sgr python3 -m venv "$BASE/venv"
sudo -u sgr "$BASE/venv/bin/pip" install -q --upgrade pip
sudo -u sgr "$BASE/venv/bin/pip" install -q -r "$APP/requirements.txt"

# -----------------------------------------------------------------------------
if [ ! -f "$ENVF" ]; then
  paso "Configuración (.env)"
  # Dirección pública de la EC2 (metadatos IMDSv2; si no, servicio externo).
  TOKEN="$(curl -s -m 2 -X PUT http://169.254.169.254/latest/api/token -H 'X-aws-ec2-metadata-token-ttl-seconds: 60' || true)"
  IP="$(curl -s -m 2 -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/public-ipv4 || true)"
  DNS="$(curl -s -m 2 -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/public-hostname || true)"
  [[ "$IP" =~ ^[0-9.]+$ ]] || IP="$(curl -s -m 5 https://checkip.amazonaws.com || true)"
  IP="$(echo "$IP" | tr -d '[:space:]')"
  [[ "$DNS" =~ ^[a-z0-9.-]+$ ]] || DNS=""
  HOSTS="localhost,127.0.0.1${IP:+,$IP}${DNS:+,$DNS}"
  ORIGENES="${IP:+http://$IP}${DNS:+,http://$DNS}"

  echo
  echo "Correo de recuperación de contraseña:"
  echo "  El código del usuario 'superadmin' llegará al correo personal que indique."
  echo "  Para enviarlo se usa una cuenta Gmail con 'contraseña de aplicación'"
  echo "  (myaccount.google.com > Seguridad > Verificación en 2 pasos > Contraseñas de aplicaciones)."
  echo "  Deje en blanco para omitir: el código se verá en el log del servidor."
  preguntar SGR_CORREO_ADMIN "  Su correo personal: "
  preguntar SGR_GMAIL "  Cuenta Gmail que envía (puede ser la misma): "
  if [ -n "${SGR_GMAIL:-}" ]; then
    preguntar SGR_GMAIL_CLAVE "  Contraseña de aplicación de Gmail (16 letras, no se muestra): " oculto
  fi
  SGR_GMAIL_CLAVE="$(echo "${SGR_GMAIL_CLAVE:-}" | tr -d '[:space:]')"
  SGR_CLAVE_DEMO="${SGR_CLAVE_DEMO:-Sgr.$(aleatorio 9)1}"
  DB_CLAVE="$(aleatorio 24)"

  (umask 027; cat > "$ENVF") <<EOF
# Generado por deploy/instalar_ec2.sh el $(date '+%Y-%m-%d %H:%M'). NO subir al repositorio.
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=$(aleatorio 50)
DJANGO_ALLOWED_HOSTS=$HOSTS
DJANGO_CSRF_TRUSTED_ORIGINS=$ORIGENES
COOKIES_SEGURAS=0
SGR_VERSION=v2.0.0-entrega2

DB_ENGINE=mysql
DB_NAME=sgr
DB_USER=sgr
DB_PASSWORD=$DB_CLAVE
DB_HOST=127.0.0.1
DB_PORT=3306

EMAIL_HOST=${SGR_GMAIL:+smtp.gmail.com}
EMAIL_PORT=587
EMAIL_USE_TLS=1
EMAIL_HOST_USER=${SGR_GMAIL:-}
EMAIL_HOST_PASSWORD=${SGR_GMAIL_CLAVE}
EMAIL_FROM="SGR La Serena <${SGR_GMAIL:-no-responder@sgr.local}>"

SGR_CORREO_ADMIN=${SGR_CORREO_ADMIN:-}
SGR_CLAVE_DEMO=$SGR_CLAVE_DEMO
EOF
  chown sgr:www-data "$ENVF"; chmod 640 "$ENVF"

  paso "Base de datos MariaDB"
  mysql -uroot <<SQL
CREATE DATABASE IF NOT EXISTS sgr CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'sgr'@'localhost' IDENTIFIED BY '$DB_CLAVE';
ALTER USER 'sgr'@'localhost' IDENTIFIED BY '$DB_CLAVE';
GRANT ALL PRIVILEGES ON sgr.* TO 'sgr'@'localhost';
FLUSH PRIVILEGES;
SQL
else
  paso "Se conserva la configuración existente ($ENVF)"
fi

# -----------------------------------------------------------------------------
paso "Migraciones, archivos estáticos y datos de prueba"
cd "$APP"
sudo -u sgr "$BASE/venv/bin/python" manage.py migrate --noinput
sudo -u sgr "$BASE/venv/bin/python" manage.py collectstatic --noinput -v0
sudo -u sgr "$BASE/venv/bin/python" manage.py cargar_datos_demo

paso "Servicios (gunicorn + nginx)"
cp "$APP/deploy/nginx-sgr.conf" /etc/nginx/sites-available/sgr
ln -sf /etc/nginx/sites-available/sgr /etc/nginx/sites-enabled/sgr
rm -f /etc/nginx/sites-enabled/default
nginx -t -q
if con_systemd; then
  cp "$APP/deploy/sgr.service" /etc/systemd/system/sgr.service
  systemctl daemon-reload
  systemctl enable -q sgr nginx
  systemctl restart sgr nginx
else
  # Entornos sin systemd (contenedores de prueba): arranque directo.
  pkill -f "gunicorn sgr.wsgi" || true
  (cd "$APP" && sudo -u sgr nohup "$BASE/venv/bin/gunicorn" sgr.wsgi:application -c deploy/gunicorn.conf.py \
     > "$BASE/gunicorn.log" 2>&1 &)
  (pgrep -x nginx >/dev/null && nginx -s reload) || nginx
fi

paso "Verificación"
for i in $(seq 1 30); do curl -fs -o /dev/null http://127.0.0.1/salud/ && break; sleep 1; done
curl -fsS http://127.0.0.1/salud/ && echo "  (aplicación y base de datos OK)"

set -a; . "$ENVF"; set +a
if [ -n "${EMAIL_HOST:-}" ] && [ -n "${SGR_CORREO_ADMIN:-}" ]; then
  sudo -u sgr "$BASE/venv/bin/python" manage.py probar_correo "$SGR_CORREO_ADMIN" \
    || echo "  !! El correo no se pudo enviar: revise la cuenta Gmail y la contraseña de aplicación en $ENVF"
fi

IP_MOSTRAR="$(echo "${DJANGO_ALLOWED_HOSTS}" | cut -d, -f3)"
cat <<FIN

=============================================================================
 SGR instalado · versión $(sudo -u sgr git -C "$APP" describe --tags --always)
 URL:          http://${IP_MOSTRAR:-<ip-publica-de-la-ec2>}
 Usuario:      superadmin   (también: coordinador, delegado, funcionario)
 Contraseña:   ${SGR_CLAVE_DEMO}
 Correo admin: ${SGR_CORREO_ADMIN:-(no configurado: el código se ve con 'journalctl -u sgr')}
 Configuración: $ENVF   (guárdela; no la suba al repositorio)

 Si la URL no abre desde su navegador: en la consola de AWS, Security Group
 de la instancia, agregue una regla de entrada HTTP (puerto 80) desde 0.0.0.0/0.
 Para actualizar más adelante: sudo bash $APP/deploy/actualizar.sh
=============================================================================
FIN
