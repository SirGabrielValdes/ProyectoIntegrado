# Informe de prueba de estrés

- **Entorno:** ENSAYO LOCAL DE REFERENCIA (no es AWS): contenedor Linux 4 vCPU / 16 GB, gunicorn 4 workers, SQLite, DEBUG=0, mismo equipo genera la carga
- **Herramienta:** Locust (`pruebas/estres/locustfile.py`), carga progresiva por etapas
- **Solicitudes totales:** 3658 · **Fallidas:** 0
- **Solicitudes por segundo (promedio):** 30.4
- **Latencia promedio:** 124 ms · **p95:** 760 ms · **máxima:** 2127 ms
- **Umbrales de aceptación:** p95 ≤ 1000 ms y errores ≤ 1.0 % por etapa

> Este ensayo valida los scripts y entrega una línea base. **No sustituye la prueba en AWS**, que queda pendiente de ejecución por el equipo según docs/pruebas/plan_pruebas_estres.md.

## Resultados por nivel de concurrencia

| Usuarios | Solicitudes/s | Latencia prom. (ms) | p95 (ms) | Errores acumulados (%) | ¿Cumple? |
|---|---|---|---|---|---|
| 2 | 0.0 | 141 | 0 | 0.00 | Sí |
| 4 | 0.0 | 121 | 350 | 0.00 | Sí |
| 6 | 6.0 | 117 | 360 | 0.00 | Sí |
| 8 | 6.0 | 107 | 350 | 0.00 | Sí |
| 10 | 7.7 | 54 | 350 | 0.00 | Sí |
| 15 | 6.9 | 62 | 340 | 0.00 | Sí |
| 20 | 6.8 | 67 | 350 | 0.00 | Sí |
| 25 | 15.5 | 51 | 430 | 0.00 | Sí |
| 35 | 16.3 | 61 | 390 | 0.00 | Sí |
| 45 | 16.2 | 75 | 580 | 0.00 | Sí |
| 50 | 30.9 | 58 | 580 | 0.00 | Sí |
| 70 | 32.9 | 62 | 330 | 0.00 | Sí |
| 90 | 32.6 | 98 | 1100 | 0.00 | No (degradación) |
| 100 | 57.2 | 124 | 1900 | 0.00 | No (degradación) |

## Resultados por operación

| Operación | Solicitudes | Fallidas | Prom. (ms) | p95 (ms) | Máx. (ms) | Solic./s |
|---|---|---|---|---|---|---|
| GET API sub atenciones | 386 | 0 | 72 | 560 | 1782 | 3.2 |
| GET API vecinos | 131 | 0 | 62 | 170 | 1864 | 1.1 |
| GET Atenciones: exportar Excel | 74 | 0 | 190 | 1000 | 1504 | 0.6 |
| GET Atenciones: listar/buscar | 524 | 0 | 73 | 400 | 1251 | 4.4 |
| GET Atención: formulario | 131 | 0 | 68 | 490 | 1159 | 1.1 |
| POST Atención: registrar | 131 | 0 | 37 | 110 | 1107 | 1.1 |
| GET GET login | 322 | 0 | 149 | 760 | 1880 | 2.7 |
| GET Inicio | 625 | 0 | 99 | 710 | 1904 | 5.2 |
| POST POST login | 319 | 0 | 498 | 1500 | 2127 | 2.7 |
| POST POST logout | 235 | 0 | 54 | 180 | 1273 | 2.0 |
| GET Sub atenciones: filtrar | 163 | 0 | 80 | 700 | 1347 | 1.4 |
| GET Usuarios: buscar | 264 | 0 | 97 | 770 | 1425 | 2.2 |
| GET Ítems: buscar/paginar | 353 | 0 | 85 | 570 | 1819 | 2.9 |

## CPU y memoria

- CPU del sistema: promedio 32 %, máximo 86 %
- Memoria de la aplicación (gunicorn): promedio 327 MB, máximo 341 MB
- Muestras: 25 (archivo `docs/pruebas/estres/ensayo_local_recursos.csv`)
