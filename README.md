# SGR · Sistema de Gestión de Requerimientos

**Proyecto Integrado · Ilustre Municipalidad de La Serena · Segunda evaluación**

Aplicación web para el registro de la atención ciudadana en las delegaciones municipales de La Serena. Incluye:

- acceso por usuario o correo, con recuperación de contraseña mediante un código de 6 dígitos;
- seis mantenedores (CRUD);
- ingreso de atenciones con catálogos dependientes y contexto de delegación;
- permisos por rol, validados en el servidor.

Todas las pantallas usan un mismo template con la identidad visual institucional (Rojo Heráldico `#C41230`).

| | |
|---|---|
| **Versión de la entrega** | `v2.0.0-entrega2`. La misma versión aparece en el pie de cada pantalla y se fija con la etiqueta Git de la entrega |
| **URL AWS** | `http://<IP-ELÁSTICA-O-DOMINIO>` ← *completar al desplegar (ver `docs/despliegue_aws.md`)* |
| **Acceso de evaluación** | Usuarios de prueba en `docs/roles_y_permisos.md`. La contraseña se entrega al docente por un canal privado |

## Integrantes

| Nombre | Rol en el equipo | Correo |
|---|---|---|
| [Nombre integrante 1] | [Rol] | [correo] |
| [Nombre integrante 2] | [Rol] | [correo] |
| [Nombre integrante 3] | [Rol] | [correo] |
| [Nombre integrante 4] | [Rol] | [correo] |

**Asignatura:** [Nombre de la asignatura] · **Docente:** [Nombre del docente] · **Sección:** [Sección]

---

## Requisitos

- Python 3.11 o superior (probado con 3.13)
- MySQL 8 o MariaDB 10.6 o superior en producción (probado con MariaDB 10.11). En desarrollo se usa SQLite sin configuración
- Navegador moderno (Chrome, Edge, Firefox o Safari)
- Para pruebas de interfaz y de estrés: `requirements-dev.txt` (Playwright, Locust)

## Tecnologías

| Capa | Tecnología |
|---|---|
| Backend | Django 5.2 (Python), plantillas del servidor |
| Base de datos | MySQL / MariaDB (PyMySQL); SQLite en desarrollo |
| Interfaz | HTML + CSS propio (template institucional), JavaScript sin framework, **SweetAlert2 11** (incluido localmente) |
| Exportación | openpyxl (Excel .xlsx) |
| Despliegue | AWS EC2 + nginx + gunicorn + systemd, RDS MySQL (o MariaDB en la EC2) |
| Pruebas | Django TestCase (funcionales), Playwright (interfaz), Locust (estrés) |

## Instalación local

```bash
git clone <url-del-repositorio> sgr && cd sgr
python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # en local: DJANGO_DEBUG=1 y DB_ENGINE=sqlite (o deje DB_* para MySQL)
python manage.py migrate
python manage.py createcachetable
python manage.py cargar_datos_demo
python manage.py runserver
```

Abra <http://127.0.0.1:8000> e ingrese con `superadmin`, `coordinador`, `delegado` o `funcionario` y la contraseña definida en `SGR_CLAVE_DEMO`.

> Sin `EMAIL_HOST`, el correo con el código de recuperación se imprime en la consola del servidor.

## Configuración

Toda la configuración se lee desde variables de entorno o desde el archivo `.env`. Use `.env.example` como plantilla: no contiene secretos.

| Variable | Descripción |
|---|---|
| `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` | Seguridad y dominios de Django |
| `DB_ENGINE` (`mysql` o `sqlite`), `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Base de datos |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `EMAIL_FROM` | SMTP para el código de recuperación (Amazon SES o Gmail) |
| `RECUPERACION_VIGENCIA_MINUTOS` (10), `RECUPERACION_ESPERA_REENVIO_SEG` (45), `RECUPERACION_MAX_INTENTOS` (5), `RECUPERACION_MAX_REENVIOS` (3), `RECUPERACION_MAX_SOLICITUDES_HORA` (3) | Límites de la recuperación. 10 min y 45 s son los valores referenciales del diseño |
| `LOGIN_MAX_INTENTOS` (5), `LOGIN_BLOQUEO_MINUTOS` (5), `SESSION_MINUTOS` (60) | Límites del acceso y duración de la sesión |
| `COOKIES_SEGURAS`, `FORZAR_HTTPS`, `HSTS_SEGUNDOS` | Endurecimiento cuando se sirve por HTTPS |
| `SGR_CLAVE_DEMO`, `SGR_VERSION` | Clave de los usuarios de prueba y versión mostrada |

## Despliegue en AWS

Guía completa en **[`docs/despliegue_aws.md`](docs/despliegue_aws.md)**: servicios y componentes AWS, configuración e inicio/actualización. En resumen:

```bash
sudo bash deploy/instalar_ec2.sh <url-repositorio> <etiqueta>   # instalación inicial en la EC2
sudo nano /opt/sgr/app/.env                                     # completar secretos (solo en la EC2)
sudo bash /opt/sgr/app/deploy/actualizar.sh <etiqueta> --datos-demo
```

`GET /salud/` verifica que la aplicación responde y se conecta a la base de datos.

## Base de datos

- **Migraciones:** `*/migrations/0001_initial.py` (`python manage.py migrate`).
- **Script SQL de referencia (MySQL):** [`docs/bd/esquema_mysql.sql`](docs/bd/esquema_mysql.sql).
- **Datos de prueba ficticios:** `python manage.py cargar_datos_demo [--atenciones N --vecinos N]`. Carga 7 delegaciones, 4 roles, 7 usuarios, 25 ítems, 6 tipos, 12 sub atenciones, vecinos y atenciones.

Modelo principal: `Delegacion`, `Rol` (permisos + alcance), `Usuario` (rol + delegaciones autorizadas), `Item`, `TipoAtencion`, `SubAtencion` (→ Tipo), `Vecino` (solicitante identificado por RUT), `Atencion` (vecino, tipo, sub atención, descripción, delegación, responsable, fecha) y `SolicitudRecuperacion` (código cifrado, vigencia, intentos y reenvíos).

## Roles y permisos

Cuatro roles definidos por el equipo: **Superadministrador**, **Coordinador**, **Delegado municipal** y **Funcionario**. Cada usuario ve solo los menús, módulos y acciones de su rol, y el servidor rechaza con 403 el acceso por URL a lo no autorizado. Matriz completa en **[`docs/roles_y_permisos.md`](docs/roles_y_permisos.md)**.

La cabecera muestra siempre el distintivo de la **delegación activa** (icono + código + nombre), el nombre del usuario y su rol. Con una delegación el contexto es fijo; con varias, el selector lista solo las autorizadas y advierte si hay cambios sin guardar.

## Estado de cada módulo

Leyenda: **Operativo** = funciona con persistencia real y está probado · **Simulado** = se comporta como el real pero sin efecto definitivo · **Pendiente** = plantilla navegable sin lógica de negocio. Una función simulada no acredita persistencia real.

| Módulo / función | Estado | Detalle |
|---|---|---|
| Login (usuario o correo), cierre de sesión, rutas protegidas | **Operativo** | Bloqueo temporal por intentos, cuenta y rol inactivos |
| Recuperar contraseña: solicitar código | **Operativo** | Respuesta genérica que no revela si el correo existe; límite por hora |
| Envío del correo con el código | **Operativo** con SMTP configurado / **Simulado** sin `EMAIL_HOST` | Sin SMTP el correo se escribe en el log del servidor |
| Validar código | **Operativo** | 6 dígitos; se puede pegar y navegar con el teclado; vigencia, intentos, reenvío con espera y código de un solo uso |
| Crear nueva contraseña | **Operativo** | Solo tras una verificación válida; política visible; invalida el código usado |
| CRUD Delegaciones, Roles, Usuarios, Ítems y metas, Tipo de Atención, Sub Atención | **Operativo** | Crear, consultar, listar, editar, eliminar y activar/desactivar, con reglas de integridad |
| Búsqueda, filtros, paginador y Exportar a Excel (6 mantenedores + Atenciones) | **Operativo** | La exportación usa el filtro aplicado en todas sus páginas, sin datos sensibles |
| Ingreso de atención | **Operativo** | Vecino existente o nuevo (RUT validado), Tipo → Sub Atención dependiente, delegación, responsable y fecha automáticos, folio, sin doble envío |
| Listado y consulta de atenciones | **Operativo** | Alcance por delegación activa |
| Roles, permisos y contexto de delegación | **Operativo** | Validados en el servidor |
| Vecinos (mantenedor completo) | **Pendiente** (plantilla) | El solicitante sí se registra desde el ingreso de atención |
| Tipo de Gestión, Seguimiento, Reportes, Auditoría | **Pendiente** (plantilla) | Navegación y visualización por rol. Sus botones informan «función pendiente» y no simulan éxito |

## Pruebas

| Tipo | Comando | Resultado | Evidencia |
|---|---|---|---|
| Funcionales (71 casos: acceso, recuperación, 6 CRUD, listados, exportación, perfiles, delegación, atención, SweetAlert2) | `python manage.py test tests` | 71/71 en SQLite y MariaDB | — |
| Matriz de pruebas funcionales | `python pruebas/generar_matriz.py --responsable "Nombre"` | Genera la matriz | [`docs/pruebas/matriz_pruebas_funcionales.xlsx`](docs/pruebas/matriz_pruebas_funcionales.xlsx) / [`.md`](docs/pruebas/matriz_pruebas_funcionales.md) |
| Interfaz en navegador (12 casos, SweetAlert2 y JavaScript) | `python pruebas/e2e/pruebas_interfaz.py --url <url> --log <log-servidor>` | 12/12 | [`docs/pruebas/resultados_interfaz.md`](docs/pruebas/resultados_interfaz.md), capturas en [`docs/evidencias/`](docs/evidencias/) |
| Estrés (Locust, carga progresiva) | ver [`docs/pruebas/plan_pruebas_estres.md`](docs/pruebas/plan_pruebas_estres.md) | Ensayo local ejecutado; **AWS pendiente** | [`docs/pruebas/estres/`](docs/pruebas/estres/) |

Cada caso funcional registra requisito, módulo, precondiciones, pasos, resultado esperado y obtenido, estado, evidencia, responsable y fecha. Los defectos encontrados y su re-prueba están en el registro de defectos de `plan_pruebas_estres.md`. Las pruebas que dependen de AWS quedan como **pendientes justificadas**, no como aprobadas.

Lista de verificación de la entrega: **[`docs/lista_verificacion.md`](docs/lista_verificacion.md)** · Normas gráficas: **[`docs/normas_graficas.md`](docs/normas_graficas.md)**.

## Estructura

```
sgr/            configuración Django (settings por variables de entorno, urls)
core/           template, permisos, contexto de delegación, base CRUD, exportación, inicio, módulos pendientes
cuentas/        usuarios, roles, login y recuperación de contraseña
catalogos/      delegaciones, ítems y metas, tipos y sub atenciones
atenciones/     vecinos e ingreso/consulta de atenciones
templates/      pantallas (base institucional, acceso, CRUD, atención, errores)
static/         CSS institucional, JS (SweetAlert2, código, atención), logo y fuentes
tests/          pruebas funcionales automatizadas
pruebas/        matriz de pruebas, pruebas de interfaz (e2e) y de estrés
deploy/         scripts y configuración para AWS EC2 (nginx, gunicorn, systemd)
docs/           despliegue, roles, normas gráficas, BD, resultados y evidencias
```

## Entrega

Para fijar la versión entregada:

```bash
git tag -a entrega-2 -m "Segunda evaluación SGR" && git push origin entrega-2
```

y despliegue esa etiqueta en AWS con `actualizar.sh entrega-2`.
