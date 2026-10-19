# Despliegue en AWS

## Arquitectura

```
Internet ──► Security Group (puerto 80) ──► EC2 Ubuntu 24.04
                                             ├─ nginx    (puerto 80: estáticos + proxy inverso)
                                             ├─ gunicorn (127.0.0.1:8000) ─► Django SGR
                                             └─ MariaDB  (127.0.0.1:3306, base «sgr»)
Código de recuperación ──► Gmail SMTP (puerto 587) ──► correo personal del encargado
```

| Servicio / componente | Uso | Configuración |
|---|---|---|
| Amazon EC2 | Servidor de aplicación y base de datos | Ubuntu Server 24.04 LTS, `t2.micro`/`t3.micro` (capa gratuita) o `t3.small` |
| Security Group | Firewall | Entrada **HTTP 80** desde 0.0.0.0/0 y **SSH 22** desde su IP |
| IP elástica (opcional) | URL fija para la evaluación | Asociada a la instancia |
| MariaDB 10.11 | Base de datos MySQL | La instala el script en la misma EC2 |
| nginx + gunicorn + systemd | Servidor web y proceso de la app | `deploy/nginx-sgr.conf`, `deploy/gunicorn.conf.py`, `deploy/sgr.service` |
| Gmail SMTP | Envío del código de recuperación | Cuenta Gmail con contraseña de aplicación |

> Los secretos (clave de Django, de la base de datos y de Gmail) se generan o piden durante la instalación y quedan solo en `/opt/sgr/app/.env` dentro de la EC2 (permisos 640). Nunca se suben al repositorio.

## Antes de empezar: contraseña de aplicación de Gmail

Necesaria para que el código de recuperación llegue a su correo personal.

1. Entre a <https://myaccount.google.com> con la cuenta Gmail que **enviará** los correos (puede ser su misma cuenta personal).
2. *Seguridad* → active la **Verificación en 2 pasos**.
3. Busque **Contraseñas de aplicaciones** (<https://myaccount.google.com/apppasswords>) y cree una llamada «SGR». Google muestra una clave de 16 letras. Cópiela; solo se ve una vez.

## 1. Crear la instancia EC2

1. Consola AWS → EC2 → **Launch instance**.
2. Nombre `sgr`, imagen **Ubuntu Server 24.04 LTS**, tipo `t2.micro`/`t3.micro`.
3. **Key pair:** cree uno (`sgr.pem`) y guárdelo.
4. **Network settings:** marque *Allow SSH traffic* y *Allow HTTP traffic from the internet*.
5. **Launch instance**. Opcional: en *Elastic IPs*, asocie una IP fija a la instancia.

## 2. Instalar (un solo comando)

Conéctese por SSH (o con el botón **Connect → EC2 Instance Connect** de la consola) y ejecute:

```bash
git clone https://github.com/SirGabrielValdes/ProyectoIntegrado.git
cd ProyectoIntegrado
sudo bash deploy/instalar_ec2.sh
```

El script pregunta tres datos:

| Pregunta | Qué responder |
|---|---|
| Su correo personal | El correo donde quiere recibir el código de recuperación del usuario `superadmin` |
| Cuenta Gmail que envía | La cuenta Gmail del paso anterior (puede ser la misma) |
| Contraseña de aplicación | La clave de 16 letras (no se muestra al escribirla) |

Puede dejar las respuestas en blanco: el sistema funciona igual y el código se ve en el log (`sudo journalctl -u sgr -n 60`).

El script hace el resto: instala los paquetes, crea la base de datos con una clave aleatoria, genera la clave secreta, detecta la IP pública, carga los datos de prueba, arranca gunicorn y nginx, verifica la base de datos y envía un **correo de prueba** a su correo personal. Al final muestra:

```
 URL:          http://<ip-publica>
 Usuario:      superadmin   (también: coordinador, delegado, funcionario)
 Contraseña:   Sgr.xxxxxxxxxxxx1      ← generada; guárdela
 Correo admin: su-correo@gmail.com
```

## 3. Probar la recuperación de contraseña

1. Abra `http://<ip-publica>` → **¿Olvidó su contraseña?**
2. Escriba su correo personal → le llega el código de 6 dígitos (revise también *Spam*).
3. Ingrese el código y cree la nueva contraseña.

> El código llega al correo **del usuario** que lo pide. Solo `superadmin` tiene su correo personal; los demás usuarios de prueba tienen correos ficticios (`@sgr.test`). Para otros usuarios, cambie su correo en el mantenedor **Usuarios**.

## Cambios posteriores

| Necesidad | Comando en la EC2 |
|---|---|
| Traer la última versión del repositorio | `sudo bash /opt/sgr/app/deploy/actualizar.sh` |
| Desplegar una etiqueta (por ejemplo `entrega-2`) | `sudo bash /opt/sgr/app/deploy/actualizar.sh entrega-2` |
| Cambiar correo, Gmail o claves | `sudo nano /opt/sgr/app/.env` y luego `sudo bash /opt/sgr/app/deploy/actualizar.sh --datos-demo` |
| Probar el envío de correo | `cd /opt/sgr/app && sudo -u sgr /opt/sgr/venv/bin/python manage.py probar_correo su@correo.cl` |
| Ver la configuración y la contraseña de prueba | `sudo cat /opt/sgr/app/.env` |
| Ver el log de la aplicación | `sudo journalctl -u sgr -n 100` |
| Verificar versión y base de datos | `git -C /opt/sgr/app describe --tags --always` y `curl http://127.0.0.1/salud/` |

## Problemas frecuentes

| Síntoma | Solución |
|---|---|
| La URL no abre (se queda cargando) | En el Security Group de la instancia, agregue una regla de entrada **HTTP, puerto 80, 0.0.0.0/0** |
| «Bad Request (400)» | Abre la página con una IP o dominio que no está en `DJANGO_ALLOWED_HOSTS`. Por ejemplo, la IP cambió al reiniciar la instancia sin IP elástica. Agréguelo en `.env` (y también en `DJANGO_CSRF_TRUSTED_ORIGINS` con `http://`) y ejecute `actualizar.sh` |
| «Error 403 CSRF» al ingresar | Lo mismo: falta `http://<ip-o-dominio>` en `DJANGO_CSRF_TRUSTED_ORIGINS` |
| No llega el correo | Revise *Spam*. Ejecute `probar_correo`: «SMTPAuthenticationError» indica que falta la verificación en 2 pasos o que la contraseña de aplicación es incorrecta |
| Error del servidor (500) | `sudo journalctl -u sgr -n 100` muestra la causa |

## HTTPS (opcional)

Con un dominio apuntando a la IP elástica:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d sgr.su-dominio.cl
```

Luego, en `.env`: `COOKIES_SEGURAS=1`, `FORZAR_HTTPS=1`, `HSTS_SEGUNDOS=3600` y `https://` en `DJANGO_CSRF_TRUSTED_ORIGINS`. Ejecute `actualizar.sh`.

## Alternativa: base de datos en Amazon RDS

Si el curso exige RDS: cree un RDS MySQL 8 en la misma VPC, sin acceso público, y con un Security Group que permita el puerto 3306 desde la EC2. Cree la base `sgr` y su usuario, ponga `DB_HOST`, `DB_USER` y `DB_PASSWORD` en `/opt/sgr/app/.env` y ejecute `actualizar.sh --datos-demo`.

## Validación realizada

`instalar_ec2.sh` se ejecutó completo en un Ubuntu 24.04 limpio que simula la EC2: paquetes, MariaDB, `.env` generado, datos de prueba, gunicorn y nginx. Luego se verificó:

- el login de `superadmin` con la contraseña generada;
- el envío del código de recuperación al correo configurado como personal (con un servidor SMTP de prueba en lugar de Gmail);
- la validación del código, el cambio de contraseña y el login con la clave nueva.

El envío real por Gmail depende de la cuenta y de la contraseña de aplicación de cada equipo.
