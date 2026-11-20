# API REST para la App Móvil (v1)

Base: `https://<servidor>/api/v1/` · Formato: JSON · Código: `tubo/api.py`

## Autenticación

1. La app pide un token con el usuario o correo y la clave del funcionario.
2. Las demás llamadas envían la cabecera `Authorization: Token <token>`.

- El token vence a los **30 días** y en la base solo se guarda su hash SHA-256.
- Tras 5 intentos fallidos se bloquea 5 minutos (respuesta 429).
- Las cuentas con **clave provisoria** deben cambiarla primero en el sitio web (respuesta 403).
- Cada llamada valida en el servidor el permiso del rol y las delegaciones autorizadas.

```http
POST /api/v1/token/
Content-Type: application/json

{"identificador": "funcionario", "clave": "********"}
```

```json
201 Created
{"token": "q1w2e3…", "expira": "2026-12-20T10:00:00-03:00",
 "usuario": {"nombre": "Fernanda Funcionaria", "rol": "Funcionario"}}
```

## Endpoints

| Método y ruta | Permiso | Descripción |
|---|---|---|
| `POST /api/v1/token/` | — | Emite un token (201). Errores: 400 (faltan datos), 401 (credenciales), 403 (cuenta inactiva o con clave provisoria), 429 (bloqueo) |
| `GET /api/v1/compromisos/` | `tubo.ver` | Compromisos de sus delegaciones. Filtros: `?asignados=1` (solo los suyos) y `?estado=EN_PROCESO` |
| `GET /api/v1/compromisos/<id>/` | `tubo.ver` | Detalle con sus evidencias y el estado de revisión |
| `POST /api/v1/compromisos/<id>/evidencias/` | `tubo.editar` | Sube una foto (multipart: `foto` y `descripcion`). Queda **pendiente de revisión** del delegado, con origen «App móvil» |

Ejemplo de carga de evidencia:

```bash
curl -X POST https://<servidor>/api/v1/compromisos/5/evidencias/ \
     -H "Authorization: Token q1w2e3…" \
     -F "foto=@poda.jpg" -F "descripcion=Poda terminada"
```

```json
201 Created
{"id": 12, "estado": "PENDIENTE", "mensaje": "Evidencia recibida; queda pendiente de revisión del delegado.",
 "compromiso": "/api/v1/compromisos/5/"}
```

Reglas de la foto: JPG, PNG o WEBP, máximo 8 MB y una imagen real (se verifica con Pillow). Un compromiso ya realizado no admite nuevas evidencias.

## Códigos de respuesta

`200` OK · `201` creado · `400` datos inválidos · `401` sin token, token inválido o vencido · `403` sin permiso o cuenta no habilitada · `404` compromiso inexistente o de otra delegación · `429` demasiados intentos.

## Pruebas

`tests/test_etapa3.py` → `ApiMovilTests` (token, listado por delegación, carga desde la app y casos de seguridad).
