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

Se genera desde `core/permisos.py`. V = ver/listar · C = crear · E = editar · D = eliminar/desactivar · X = exportar a Excel · A = aprobar/validar (felicitaciones y evidencias fotográficas).
Los módulos marcados como *plantilla* tienen navegación e interfaz, pero su lógica de negocio queda pendiente.

| Módulo | Superadministrador | Coordinador | Delegado municipal | Funcionario |
|---|---|---|---|---|
| Inicio | V | V | V | V |
| Delegaciones | V C E D X | V X | V | — |
| Roles y permisos | V C E D X | V | — | — |
| Usuarios | V C E D X | V C E D X | V X | — |
| Ítems de la matriz | V C E D X | V C E D X | V X | — |
| Tipo de Atención | V C E D X | V C E D X | V | — |
| Sub Atención | V C E D X | V C E D X | V | — |
| Atenciones | V C X | V C X | V C X | V C |
| Trimestres y metas | V C E D X | V C E D X | V | — |
| JJVV y organizaciones | V C E D X | V C E D X | V C E D X | V |
| Matriz de actividades | V C D X A | V X A | V C D X A | V C D |
| Ausencias (semáforo) | V C E D X | V C E D X | V C E D X | — |
| Tubo de trabajo | V C E X A | V C E X A | V C E X A | V C E |
| Áreas de apoyo | V C E D X | V C E D X | V | — |
| Dashboard general | V | V | — | — |
| Dashboard por delegación | V | V | V | — |
| Dashboard por funcionario | V | V | V | V |
| Vecinos *(plantilla)* | V | V | V | V |
| Tipo de Gestión *(plantilla)* | V | V | — | — |
| Reportes *(plantilla)* | V | V | V | — |
| Auditoría *(plantilla)* | V | — | — | — |

## Cargos (descriptor de funciones)

Además del rol de permisos, cada funcionario tiene un **cargo** que define sus metas en la matriz SGR: Delegado, Gestor Social, Apoyo Administrativo, Organizaciones Comunitarias, Gestor de Compras y Proyectos, Gestión y Planificación, y Coordinador de Servicios Comunitarios. El Superadministrador y el Coordinador no tienen cargo, por lo que no tienen metas.

## Reglas de alcance (validadas en el servidor)

- **Menú:** al iniciar sesión cada usuario ve solo los módulos con permiso `ver` (`core/context_processors.py`).
- **Vistas:** cada vista exige su permiso con `@requiere_permiso` (`core/permisos.py`). Abrir una URL sin permiso responde **403**, aunque el botón no se muestre.
- **Delegación activa:** se guarda en la sesión y se valida en cada solicitud contra las delegaciones autorizadas (`core/middleware.py`). Un valor alterado se reemplaza por una delegación autorizada.
- **Cambio de contexto:** solo con POST y solo hacia delegaciones autorizadas; otro valor responde **403**.
- **Usuarios:** fuera del alcance global solo se listan usuarios de la delegación activa y nunca cuentas globales. Un Coordinador no puede asignar roles globales, roles con más permisos que el suyo ni delegaciones que no administra.
- **Roles:** nadie puede otorgar permisos que su propio rol no tiene. Solo el Superadministrador crea roles globales.
- **Atenciones:** la delegación y el usuario responsable se toman de la sesión, no del formulario. Las atenciones de otra delegación responden **404** aunque se abra su URL.
- **Exportaciones:** usan el mismo filtro y alcance del listado, en todas sus páginas, sin contraseñas, tokens ni campos internos.
- **Matriz de actividades:** el funcionario ve solo sus actividades; el delegado (permiso «aprobar») ve las de toda su delegación y es el único que registra felicitaciones.
- **Dashboards:** el general muestra las delegaciones autorizadas; el de funcionario muestra el propio, y el delegado puede ver el de su equipo, pero no el de funcionarios de otras delegaciones (404).
- **Tubo de trabajo:** los compromisos, las fotos y la API móvil se limitan a la delegación del usuario. Las fotos no se publican: se sirven por una vista que valida el permiso.

## Usuarios de prueba

| Usuario | Rol | Cargo | Delegaciones |
|---|---|---|---|
| superadmin | Superadministrador | — | Todas (global) |
| coordinador | Coordinador | — | DEL-00001, DEL-00002, DEL-00003 |
| delegado / delegado2 | Delegado municipal | Delegado | DEL-00001 / DEL-00002 |
| funcionario | Funcionario | Gestor Social | DEL-00001 |
| funcionario2 | Funcionario | Organizaciones Comunitarias | DEL-00002 |
| apoyo | Funcionario | Apoyo Administrativo | DEL-00001 |
| servicios | Funcionario | Coordinador de Servicios Comunitarios | DEL-00001 |
| planificacion | Funcionario | Gestión y Planificación | DEL-00002 |
| inactivo | Funcionario (cuenta inactiva) | Apoyo Administrativo | DEL-00001 |

La contraseña es la definida en `SGR_CLAVE_DEMO` del archivo `.env`. Se entrega al docente por un canal privado; no se publica en el repositorio.
