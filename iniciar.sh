#!/usr/bin/env bash
# Inicia el SGR en modo desarrollo local (Linux / macOS).
# Uso: ./iniciar.sh        -> instala, prepara la base SQLite con datos de prueba y abre el servidor
set -e
cd "$(dirname "$0")"
PY=python3
command -v $PY >/dev/null 2>&1 || PY=python
if [ ! -d .venv ]; then
  echo "==> Creando entorno virtual (.venv)"
  $PY -m venv .venv
fi
source .venv/bin/activate
echo "==> Instalando dependencias"
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt
echo "==> Preparando base de datos"
python manage.py migrate
python manage.py cargar_datos_demo
echo
echo "Listo. Abra http://127.0.0.1:8000  (usuario: superadmin  ·  clave: Serena.2026)"
echo "Para detener el servidor presione Ctrl+C."
python manage.py runserver
