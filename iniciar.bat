@echo off
REM Inicia el SGR en modo desarrollo local (Windows). Doble clic o: iniciar.bat
cd /d "%~dp0"
where py >nul 2>nul && (set PY=py) || (set PY=python)
if not exist .venv (
  echo ==^> Creando entorno virtual .venv
  %PY% -m venv .venv || goto error
)
call .venv\Scripts\activate.bat
echo ==^> Instalando dependencias
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt || goto error
echo ==^> Preparando base de datos
python manage.py migrate || goto error
python manage.py cargar_datos_demo || goto error
echo.
echo Listo. Abra http://127.0.0.1:8000  (usuario: superadmin - clave: Serena.2026)
echo Para detener el servidor presione Ctrl+C.
python manage.py runserver
goto :eof
:error
echo.
echo Ocurrio un error. Verifique que Python 3.11 o superior este instalado (python.org) y vuelva a intentar.
pause
