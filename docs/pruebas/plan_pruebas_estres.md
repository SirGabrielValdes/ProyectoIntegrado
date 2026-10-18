# Plan y registro de pruebas de estrés

## Objetivo

Evaluar las operaciones integradas (con base de datos) aumentando progresivamente
la concurrencia hasta observar degradación o alcanzar el límite seguro del entorno.

## Definición previa (antes de ejecutar)

| Elemento | Definición |
|---|---|
| Herramienta | Locust 2.x (`pruebas/estres/locustfile.py`) en modo *headless* con `--csv` y `--html` |
| Generador de carga | Equipo del integrante o una segunda EC2 en la misma región (no la instancia evaluada) |
| Entorno evaluado | EC2 `t3.small` + RDS MySQL `db.t3.micro` (completar con lo usado realmente) |
| Volumen de datos | `cargar_datos_demo --atenciones 5000 --vecinos 1000` (7 delegaciones, 7 usuarios, 25 ítems, 12 sub atenciones) |
| Escenarios | Funcionario (60 %): inicio, buscar/paginar atenciones, sub atenciones dependientes, **registrar atención**. Coordinador (40 %): buscar/paginar ítems, usuarios y sub atenciones, **exportar a Excel**. Acceso: login y logout |
| Carga y duración | Etapas de 2 min: 10 → 25 → 50 → 100 → 150 usuarios (`SGR_ETAPAS="10:120,25:120,50:120,100:120,150:120"`) |
| Carga objetivo | 50 usuarios concurrentes (tamaño estimado de los equipos de delegaciones en horario punta) |
| Umbrales de aceptación | p95 ≤ 1000 ms por etapa · errores ≤ 1 % · sin caída del servicio · recuperación < 60 s al bajar la carga |
| Criterio de detención | p95 > 3000 ms sostenido, errores > 5 % o CPU de la EC2 > 95 % por más de 1 min (límite seguro) |
| Métricas | Solicitudes/s, latencia promedio y p95, errores, CPU y memoria (`monitor_recursos.py` o CloudWatch) |

## Procedimiento

```bash
# 1) En la EC2 (datos de volumen y monitor de recursos)
sudo -u sgr /opt/sgr/venv/bin/python /opt/sgr/app/manage.py cargar_datos_demo --atenciones 5000 --vecinos 1000
sudo /opt/sgr/venv/bin/pip install psutil
sudo /opt/sgr/venv/bin/python /opt/sgr/app/pruebas/estres/monitor_recursos.py --salida /tmp/recursos.csv --segundos 720

# 2) En el generador de carga
pip install -r requirements-dev.txt
export SGR_CLAVE_DEMO=<clave de evaluación>
SGR_ETAPAS="10:120,25:120,50:120,100:120,150:120" locust -f pruebas/estres/locustfile.py \
   --host http://<ip-elastica> --headless --csv docs/pruebas/estres/aws --csv-full-history \
   --html docs/pruebas/estres/aws_reporte.html

# 3) Recuperación: tras terminar, medir que /salud/ responde y la latencia vuelve a la línea base
for i in $(seq 1 12); do curl -s -o /dev/null -w "%{http_code} %{time_total}\n" http://<ip-elastica>/salud/; sleep 5; done

# 4) Informe
scp ubuntu@<ip>:/tmp/recursos.csv docs/pruebas/estres/aws_recursos.csv
python pruebas/estres/resumir.py --prefijo docs/pruebas/estres/aws --recursos docs/pruebas/estres/aws_recursos.csv \
   --entorno "AWS EC2 t3.small + RDS MySQL db.t3.micro, región us-east-1" --salida docs/pruebas/estres/informe_aws.md
```

## Estado de ejecución

| Prueba | Entorno | Estado | Evidencia |
|---|---|---|---|
| Ensayo de referencia (validación de scripts) | Local: 4 vCPU, gunicorn 4 workers, SQLite, DEBUG=0 | **Ejecutada** | `estres/ensayo_local_informe.md`, `estres/ensayo_local_reporte.html` |
| Prueba de estrés oficial | AWS (EC2 + RDS) | **Pendiente**: requiere la instancia AWS del equipo. No se declara aprobada. | `estres/informe_aws.md` (por generar) |

### Hallazgos del ensayo local (referencial)

- 3.658 solicitudes, **0 errores**, 30 solicitudes/s en promedio y 57 solicitudes/s con 100 usuarios.
- Se cumple el umbral (p95 ≤ 1000 ms) hasta unos 70 usuarios concurrentes; con 90 a 100 usuarios el p95 sube a 1,1–1,9 s (**degradación observada**). El generador de carga y el servidor compartían CPU (máximo 86 %), lo que acelera la degradación.
- La operación más costosa es `POST login` (≈ 500 ms promedio), por el cifrado intencionalmente lento de contraseñas (PBKDF2). Es un costo de seguridad esperado.
- Acción para AWS: usar `GUNICORN_WORKERS` = 2×vCPU+1, y generar la carga desde otro equipo para no contaminar la medición.

## Registro de defectos detectados y corregidos

| ID | Detectado en | Defecto | Corrección | Re-prueba |
|---|---|---|---|---|
| DEF-01 | Pruebas funcionales (PF de validaciones) | Un formulario enviado completamente vacío se trataba como no enviado y no mostraba errores | Los formularios se vinculan siempre que el método es POST (`core/crud.py`, `cuentas/views.py`) | Aprobada (`test_requeridos_formato_longitud_duplicado`, `test_login_campos_vacios`) |
| DEF-02 | Revisión visual (Playwright) | Los bloques ocultos con el atributo `hidden` se mostraban por reglas `display` del CSS (ingreso de atención) | Regla global `[hidden] { display: none !important; }` | Aprobada (UI-09) |
| DEF-03 | Pruebas sobre MariaDB | MariaDB no crea restricciones únicas sobre expresiones (unicidad sin distinguir mayúsculas) | Normalización (códigos en mayúsculas; usuario y correo en minúsculas) más `unique=True` en la base | Aprobada: 71/71 en SQLite y MariaDB |
| DEF-04 | Revisión visual móvil | La cabecera no cabía en 390 px (botón Salir fuera de pantalla) | Ajustes responsivos de la cabecera y del distintivo | Aprobada (UI-12) |
| DEF-05 | Revisión de permisos | El rol de sistema respondía «sí» a cualquier código de permiso, incluso inexistente (p. ej. `atenciones.editar`), y mostraba enlaces rotos | Se limita al catálogo `TODOS_LOS_PERMISOS` | Aprobada (UI-03, PF de menús) |
