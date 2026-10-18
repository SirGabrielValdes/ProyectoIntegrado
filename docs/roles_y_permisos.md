# Roles, permisos y alcance por delegación

Definición del equipo para la segunda entrega. Los roles se cargan con
`python manage.py cargar_datos_demo` (fuente: `core/permisos.py`) y pueden
modificarse desde el mantenedor **Roles**.

## Roles

| Código | Rol | Alcance | Descripción |
|---|---|---|---|
| ROL01 | Superadministrador | Global (todas las delegaciones) | Administra todo el sistema. Rol protegido: no se elimina, no se desactiva y conserva todos los permisos. |
| ROL02 | Coordinador | Varias delegaciones autorizadas | Coordina varias delegaciones: administra usuarios de sus delegaciones y los catálogos de atención. |
| ROL03 | Delegado municipal | Una delegación | Responsable de una delegación: consulta su equipo y catálogos, registra y supervisa atenciones. |
| ROL04 | Funcionario | Una delegación | Operador de atención ciudadana: registra y consulta atenciones de su delegación. |

## Matriz de permisos

V = ver/listar · C = crear · E = editar · D = eliminar/desactivar · X = exportar a Excel.
Los módulos marcados como *plantilla* tienen navegación e interfaz, pero su lógica de negocio queda pendiente.

| Módulo | Superadministrador | Coordinador | Delegado municipal | Funcionario |
|---|---|---|---|---|
| Inicio | V | V | V | V |
| Delegaciones | V C E D X | V X | V | — |
| Roles y permisos | V C E D X | V | — | — |
| Usuarios | V C E D X | V C E D X | V X | — |
| Ítems y metas | V C E D X | V C E D X | V X | — |
| Tipo de Atención | V C E D X | V C E D X | V | — |
| Sub Atención | V C E D X | V C E D X | V | — |
| Atenciones (ingreso y consulta) | V C X | V C X | V C X | V C |
| Vecinos *(plantilla)* | V | V | V | V |
| Tipo de Gestión *(plantilla)* | V | V | — | — |
| Seguimiento *(plantilla)* | V | V | V | — |
| Reportes *(plantilla)* | V | V | V | — |
| Auditoría *(plantilla)* | V | — | — | — |

## Reglas de alcance (validadas en el servidor)

- **Menú:** al iniciar sesión cada usuario ve solo los módulos con permiso `ver` (`core/context_processors.py`).
- **Vistas:** cada vista exige su permiso con `@requiere_permiso` (`core/permisos.py`). Abrir una URL sin permiso responde **403**, aunque el botón no se muestre.
- **Delegación activa:** se guarda en la sesión y se valida en cada solicitud contra las delegaciones autorizadas (`core/middleware.py`). Un valor alterado se reemplaza por una delegación autorizada.
- **Cambio de contexto:** solo con POST y solo hacia delegaciones autorizadas; otro valor responde **403**.
- **Usuarios:** fuera del alcance global solo se listan usuarios de la delegación activa y nunca cuentas globales. Un Coordinador no puede asignar roles globales, roles con más permisos que el suyo ni delegaciones que no administra.
- **Roles:** nadie puede otorgar permisos que su propio rol no tiene. Solo el Superadministrador crea roles globales.
- **Atenciones:** la delegación y el usuario responsable se toman de la sesión, no del formulario. Las atenciones de otra delegación responden **404** aunque se abra su URL.
- **Exportaciones:** usan el mismo filtro y alcance del listado, en todas sus páginas, sin contraseñas, tokens ni campos internos.

## Usuarios de prueba

| Usuario | Rol | Delegaciones |
|---|---|---|
| superadmin | Superadministrador | Todas (global) |
| coordinador | Coordinador | DEL01, DEL02, DEL03 |
| delegado / delegado2 | Delegado municipal | DEL01 / DEL02 |
| funcionario / funcionario2 | Funcionario | DEL01 / DEL02 |
| inactivo | Funcionario (cuenta inactiva) | DEL01 |

La contraseña es la definida en `SGR_CLAVE_DEMO` del archivo `.env`. Se entrega al docente por un canal privado; no se publica en el repositorio.
