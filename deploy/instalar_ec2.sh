#!/usr/bin/env bash
# Instalación inicial del SGR en una instancia EC2 Ubuntu 22.04/24.04.
# Uso (en la EC2):  sudo bash deploy/instalar_ec2.sh <url-del-repositorio> [rama-o-etiqueta] [--mysql-local]
#   --mysql-local  instala MariaDB en la misma EC2 (si no se usa Amazon RDS).
set -euo pipefail

REPO="${1:?Indique la URL del repositorio Git}"
REF="${2:-main}"
MYSQL_LOCAL="${3:-}"
BASE=/opt/sgr

echo "==> Paquetes del sistema"
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git nginx
if [ "$MYSQL_LOCAL" = "--mysql-local" ]; then
  apt-get install -y mariadb-server
  systemctl enable --now mariadb
fi

echo "==> Usuario y directorios"
id sgr >/dev/null 2>&1 || useradd --system --create-home --shell /usr/sbin/nologin --gid www-data sgr
mkdir -p "$BASE"
chown sgr:www-data "$BASE"

echo "==> Código ($REF)"
if [ ! -d "$BASE/app/.git" ]; then
  sudo -u sgr git clone "$REPO" "$BASE/app"
fi
sudo -u sgr git -C "$BASE/app" fetch --all --tags
sudo -u sgr git -C "$BASE/app" checkout "$REF"

echo "==> Entorno virtual y dependencias"
sudo -u sgr python3 -m venv "$BASE/venv"
sudo -u sgr "$BASE/venv/bin/pip" install --upgrade pip
sudo -u sgr "$BASE/venv/bin/pip" install -r "$BASE/app/requirements.txt"

if [ ! -f "$BASE/app/.env" ]; then
  cp "$BASE/app/.env.example" "$BASE/app/.env"
  chown sgr:www-data "$BASE/app/.env"
  chmod 640 "$BASE/app/.env"
  echo "!! Complete $BASE/app/.env (clave secreta, base de datos, correo) y vuelva a ejecutar deploy/actualizar.sh"
fi

if [ "$MYSQL_LOCAL" = "--mysql-local" ]; then
  echo "==> Base de datos local: ejecute 'sudo mysql < deploy/crear_bd_local.sql' tras definir la clave en ese archivo"
fi

echo "==> Servicios"
cp "$BASE/app/deploy/sgr.service" /etc/systemd/system/sgr.service
cp "$BASE/app/deploy/nginx-sgr.conf" /etc/nginx/sites-available/sgr
ln -sf /etc/nginx/sites-available/sgr /etc/nginx/sites-enabled/sgr
rm -f /etc/nginx/sites-enabled/default
systemctl daemon-reload
systemctl enable sgr nginx
nginx -t && systemctl restart nginx
echo "Instalación base lista. Siguiente paso: completar .env y ejecutar 'sudo bash $BASE/app/deploy/actualizar.sh $REF'"
