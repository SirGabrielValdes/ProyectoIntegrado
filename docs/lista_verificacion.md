# Lista de verificación de la segunda evaluación

Correspondencia entre la lista del documento de requisitos (A4) y las evidencias del repositorio.

| Nº | Evidencia requerida | Dónde se demuestra | Estado |
|---|---|---|---|
| 1 | Login y flujo completo de recuperación: solicitar código, validarlo y crear nueva contraseña | `cuentas/views.py`, `templates/auth/`. Pruebas `tests/test_acceso.py` (22 casos) y UI-01, UI-02, UI-04. Capturas `docs/evidencias/01`–`08` | Operativo y probado |
| 2 | Seis CRUD: Delegaciones, Roles, Usuarios, Ítems y metas, Tipo de Atención y Sub Atención | `catalogos/views.py`, `cuentas/views.py`, base común en `core/crud.py`. Pruebas `tests/test_mantenedores.py`, UI-05 a UI-07 | Operativo y probado |
| 3 | Ingreso de atención con dependencia de catálogos y contexto de delegación | `atenciones/views.py`, `static/js/atencion.js`. Pruebas `IngresoAtencionTests` y UI-09. Capturas 17 y 18 | Operativo y probado |
| 4 | Tabla, paginador, búsqueda y Exportar a Excel en cada mantenedor | `templates/crud/lista.html`, `Mantenedor.vista_exportar`. Pruebas de listados y exportación, UI-05 | Operativo y probado |
| 5 | Normas gráficas oficiales; identificación de delegación, usuario y rol; alcance según perfil | `docs/normas_graficas.md`, `templates/base.html`, `docs/roles_y_permisos.md`. Pruebas `PerfilesTests`, UI-03, UI-08, UI-11 | Operativo y probado (supuestos tipográficos documentados) |
| 6 | Validaciones y mensajes SweetAlert2 en todas las funciones implementadas | `static/js/sgr.js` (mensajes del servidor, confirmaciones, validación previa y doble envío). Pruebas de error de servidor y UI-01, 02, 06, 07, 09, 10, 11 | Operativo y probado |
| 7 | URL AWS, repositorio Git y versión inequívoca de la entrega | Repositorio con historial; guía `docs/despliegue_aws.md`; scripts en `deploy/`; versión visible en el pie (`SGR_VERSION`) | Repositorio y scripts listos. **URL AWS y etiqueta pendientes**: los crea el equipo |
| 8 | Resultados de pruebas funcionales y de estrés, evidencias y correcciones | `docs/pruebas/matriz_pruebas_funcionales.xlsx` (71/71), `docs/pruebas/resultados_interfaz.md` (12/12), `docs/pruebas/plan_pruebas_estres.md` (registro de defectos), `docs/pruebas/estres/` | Funcionales: ejecutadas. Estrés: ensayo local ejecutado; **AWS pendiente** |
| 9 | Resumen de funciones operativas, simuladas y pendientes según avance de Backend | `README.md`, sección «Estado de cada módulo» | Documentado |
