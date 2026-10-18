# Despliegue en AWS

## Arquitectura

```
Internet ──► Security Group (80/443) ──► EC2 Ubuntu 24.04
                                          ├─ nginx  (puerto 80: estáticos + proxy inverso)
                                          └─ gunicorn (127.0.0.1:8000) ─► Django SGR
                                                          │
                                   Security Group (3306) ─┘──► Amazon RDS MySQL 8
                                                               (o MariaDB en la misma EC2)
Correo de recuperación ──► Amazon SES (SMTP) o Gmail SMTP
```

| Servicio / componente | Uso | Configuración sugerida (evaluación) |
|---|---|---|
| Amazon EC2 | Servidor de aplicación | Ubuntu 24.04, `t3.small` (2 vCPU, 2 GB) o `t2.micro`/`t3.micro` de la capa gratuita, IP elástica |
| Security Group de la app | Firewall | Entrada 80 (HTTP) y 443 (HTTPS) desde 0.0.0.0/0; 22 (SSH) solo desde la IP del equipo |
| Amazon RDS for MySQL 8 | Base de datos | `db.t3.micro`, 20 GB, sin acceso público, Security Group que permita 3306 solo desde el SG de la EC2 |
| Alternativa sin RDS | Base de datos local | MariaDB en la misma EC2 (`instalar_ec2.sh ... --mysql-local`) |
| Amazon SES (opcional) | Correo SMTP | Identidad de correo verificada y credenciales SMTP de SES |
| nginx | Proxy inverso y estáticos | `deploy/nginx-sgr.conf` |
| gunicorn + systemd | Proceso de la app | `deploy/gunicorn.conf.py`, `deploy/sgr.service` |

> Los secretos (clave de Django, clave de la base de datos y SMTP) solo se guardan en `/opt/sgr/app/.env` dentro de la EC2 (permisos 640). Nunca se suben al repositorio ni aparecen en las evidencias.

## 1. Crear la base de datos (RDS)

1. RDS → *Create database* → MySQL 8.0 → plantilla *Free tier* → identificador `sgr-db`.
2. Usuario maestro: `admin`; defina una clave segura (se usará solo para crear el usuario de la app).
3. Conectividad: misma VPC que la EC2, **Public access: No**, Security Group `sgr-db-sg` con entrada 3306 desde `sgr-app-sg`.
4. Cuando esté disponible, desde la EC2:
   ```bash
   sudo apt install -y mysql-client
   mysql -h <endpoint-rds> -u admin -p
   CREATE DATABASE sgr CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'sgr'@'%' IDENTIFIED BY '<clave-app>';
   GRANT ALL PRIVILEGES ON sgr.* TO 'sgr'@'%';
   FLUSH PRIVILEGES;
   ```

## 2. Crear la instancia EC2

1. EC2 → *Launch instance* → Ubuntu Server 24.04 LTS → `t3.small` (o capa gratuita).
2. Par de claves para SSH, Security Group `sgr-app-sg` (80, 443 y 22 restringido).
3. Asigne una **IP elástica** para que la URL de evaluación no cambie.

## 3. Instalación inicial

```bash
ssh -i sgr.pem ubuntu@<ip-elastica>
git clone <url-del-repositorio> /tmp/sgr && cd /tmp/sgr
sudo bash deploy/instalar_ec2.sh <url-del-repositorio> <etiqueta-entrega>     # con RDS
# o: sudo bash deploy/instalar_ec2.sh <url> <etiqueta> --mysql-local          # MariaDB en la EC2
```

Complete la configuración (vea `.env.example`):

```bash
sudo nano /opt/sgr/app/.env
#  DJANGO_SECRET_KEY=<python3 -c "import secrets; print(secrets.token_urlsafe(50))">
#  DJANGO_ALLOWED_HOSTS=<ip-elastica>,<dns-publico>,127.0.0.1
#  DJANGO_CSRF_TRUSTED_ORIGINS=http://<ip-elastica>
#  DB_HOST=<endpoint-rds>  DB_PASSWORD=<clave-app>
#  EMAIL_HOST=email-smtp.us-east-1.amazonaws.com  EMAIL_HOST_USER=...  EMAIL_HOST_PASSWORD=...
#  SGR_CLAVE_DEMO=<clave de evaluación acordada con el docente>
```

Primera puesta en marcha (migraciones, estáticos, datos de prueba y reinicio):

```bash
sudo bash /opt/sgr/app/deploy/actualizar.sh <etiqueta-entrega> --datos-demo
```

El script termina consultando `http://127.0.0.1/salud/`, que verifica la conexión a la base de datos, y muestra la versión desplegada (`git describe`).

## 4. Actualizar a una nueva versión

```bash
sudo bash /opt/sgr/app/deploy/actualizar.sh <rama|commit|etiqueta>
```

## 5. Verificar que el despliegue corresponde a la versión entregada

```bash
git -C /opt/sgr/app describe --tags --always   # debe coincidir con la etiqueta entregada
curl -s http://<ip-elastica>/salud/            # {"estado": "ok"} → app y base de datos conectadas
sudo systemctl status sgr nginx
sudo journalctl -u sgr -n 50                   # log de la aplicación
```

El pie de cada pantalla muestra `SGR_VERSION`.

## 6. HTTPS (opcional, recomendado)

Con un dominio apuntando a la IP elástica:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d sgr.su-dominio.cl
```

Luego, en `.env`: `COOKIES_SEGURAS=1`, `FORZAR_HTTPS=1`, `HSTS_SEGUNDOS=3600` y `https://` en `DJANGO_CSRF_TRUSTED_ORIGINS`. Ejecute `actualizar.sh`.

## Validación realizada

El stack de producción (nginx + gunicorn + MariaDB 10.11 con `DEBUG=0`, archivos de `deploy/`) se validó en un entorno Linux local que simula la EC2. Ahí se ejecutaron las 71 pruebas funcionales y las 12 pruebas de interfaz (`docs/pruebas/`). **La URL AWS definitiva debe registrarse en el README una vez creada la instancia.**
