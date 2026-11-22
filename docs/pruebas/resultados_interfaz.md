# Resultados de pruebas de interfaz (navegador)

Ejecución: **22-11-2026 20:12** · URL: `http://127.0.0.1:8000` (servidor de desarrollo local, SQLite) · Navegador: Chromium (Playwright) · Aprobadas: **16/16**

Generado con `python pruebas/e2e/pruebas_interfaz.py`. Capturas en `docs/evidencias/`.

| ID | Caso | Estado | Evidencia | Duración |
|---|---|---|---|---|
| UI-01 | Login incorrecto muestra SweetAlert2 de error y mensaje genérico | Aprobada | 02_login_incorrecto_swal.png | 1.3s |
| UI-02 | Login con campos vacíos se valida en la interfaz con SweetAlert2 | Aprobada | 03_login_vacio_swal.png | 0.6s |
| UI-03 | Cada rol ve solo sus menús (Superadministrador, Coordinador, Delegado municipal, Funcionario) | Aprobada | 04_inicio_*.png | 9.8s |
| UI-04 | Recuperación: solicitar, pegar código de 6 dígitos, requisitos de clave y confirmación SweetAlert2 | Aprobada | 05..08_*.png | 6.3s |
| UI-05 | Listado: búsqueda en vivo (sin botón Buscar), selector de filas, filtros conservados al paginar y Excel | Aprobada | 09_busqueda_en_vivo_filas.png, 10_sin_coincidencias.png | 3.0s |
| UI-06 | Eliminar: confirmación SweetAlert2, cancelación sin cambios y rechazo por relaciones | Aprobada | 11_confirmar_eliminar.png, 12_eliminar_rechazado_relaciones.png | 2.3s |
| UI-07 | Formulario CRUD sin campo Código: validación de requeridos en la interfaz y duplicado del servidor | Aprobada | 13_validacion_requeridos.png, 14_error_duplicado.png | 1.5s |
| UI-08 | Cambio de delegación advierte cambios sin guardar y actualiza el contexto | Aprobada | 15_advertencia_cambio_delegacion.png, 16_contexto_del02.png | 3.5s |
| UI-09 | Ingreso de atención: vecino, dependencia Tipo→Sub Atención, doble envío y folio con SweetAlert2 | Aprobada | 17_ingreso_atencion.png, 18_atencion_registrada_folio.png | 3.1s |
| UI-10 | Módulo pendiente: plantilla navegable que informa función pendiente sin simular éxito | Aprobada | 19_modulo_pendiente.png | 0.6s |
| UI-11 | Acceso por URL a módulo no autorizado muestra 403 con SweetAlert2 | Aprobada | 20_acceso_denegado_403.png | 1.5s |
| UI-12 | Diseño adaptable en pantalla móvil (390 px) con menú desplegable | Aprobada | 21_movil_inicio.png, 22_movil_menu.png | 2.5s |
| UI-13 | Usuario nuevo: clave provisoria por correo y cambio obligatorio en el primer ingreso | Aprobada | 23_usuario_nuevo_sin_clave.png, 24_cambio_clave_obligatorio.png | 14.9s |
| UI-14 | Matriz: registrar actividad con puntaje automático; felicitaciones ocultas para el funcionario | Aprobada | 25..27_*.png | 7.5s |
| UI-15 | Tubo de trabajo: mover tarjeta, aprobar evidencia y realizar; dashboards con semáforo | Aprobada | 28..31_*.png | 11.1s |
| UI-16 | Tubo de trabajo: arrastrar tarjetas solo a la etapa siguiente, con confirmación y regla de evidencia | Aprobada | 32..35_*.png | 13.6s |
