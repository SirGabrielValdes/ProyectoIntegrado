# Resultados de pruebas de interfaz (navegador)

Ejecución: **18-10-2026 23:04** · URL: `http://127.0.0.1` (simulación local del stack EC2: nginx + gunicorn + MariaDB 10.11, DEBUG=0) · Navegador: Chromium (Playwright) · Aprobadas: **12/12**

Generado con `python pruebas/e2e/pruebas_interfaz.py`. Capturas en `docs/evidencias/`.

| ID | Caso | Estado | Evidencia | Duración |
|---|---|---|---|---|
| UI-01 | Login incorrecto muestra SweetAlert2 de error y mensaje genérico | Aprobada | 02_login_incorrecto_swal.png | 1.1s |
| UI-02 | Login con campos vacíos se valida en la interfaz con SweetAlert2 | Aprobada | 03_login_vacio_swal.png | 0.6s |
| UI-03 | Cada rol ve solo sus menús (Superadministrador, Coordinador, Delegado municipal, Funcionario) | Aprobada | 04_inicio_*.png | 9.4s |
| UI-04 | Recuperación: solicitar, pegar código de 6 dígitos, requisitos de clave y confirmación SweetAlert2 | Aprobada | 05..08_*.png | 6.2s |
| UI-05 | Listado: búsqueda, filtros conservados al paginar y exportación a Excel | Aprobada | 09_items_filtro_pagina2.png, 10_sin_coincidencias.png | 2.0s |
| UI-06 | Eliminar: confirmación SweetAlert2, cancelación sin cambios y rechazo por relaciones | Aprobada | 11_confirmar_eliminar.png, 12_eliminar_rechazado_relaciones.png | 2.1s |
| UI-07 | Formulario CRUD: validación de requeridos en la interfaz y error de duplicado del servidor | Aprobada | 13_validacion_requeridos.png, 14_error_duplicado.png | 1.5s |
| UI-08 | Cambio de delegación advierte cambios sin guardar y actualiza el contexto | Aprobada | 15_advertencia_cambio_delegacion.png, 16_contexto_del02.png | 3.6s |
| UI-09 | Ingreso de atención: vecino, dependencia Tipo→Sub Atención, doble envío y folio con SweetAlert2 | Aprobada | 17_ingreso_atencion.png, 18_atencion_registrada_folio.png | 3.0s |
| UI-10 | Módulo pendiente: plantilla navegable que informa función pendiente sin simular éxito | Aprobada | 19_modulo_pendiente.png | 0.6s |
| UI-11 | Acceso por URL a módulo no autorizado muestra 403 con SweetAlert2 | Aprobada | 20_acceso_denegado_403.png | 1.4s |
| UI-12 | Diseño adaptable en pantalla móvil (390 px) con menú desplegable | Aprobada | 21_movil_inicio.png, 22_movil_menu.png | 1.2s |
