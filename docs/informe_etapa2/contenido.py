"""Contenido del Informe Etapa 2 (datos estructurados usados por generar_informe.py)."""

TITULO = "Informe Técnico de Planificación y Diseño de Producto Software"
SUBTITULO = "Etapa 2: Metodología y modelos de proceso del proyecto de software\nSistema de Gestión de Requerimientos (SGR) · Ilustre Municipalidad de La Serena"
PIE = "Informe Etapa 2 – SGR La Serena"

# --------------------------------------------------------------------------
# Fuentes de información (análisis documental)
# --------------------------------------------------------------------------
FUENTES = [
    ("F1", "Documento «Requisitos y plan de pruebas de la segunda evaluación» (Proyecto Integrado SGR)",
     "Cliente (docente en representación de la Municipalidad)", "10 páginas: módulos (A1), requisitos de interfaz y contexto (A2), validaciones y pruebas (A3), despliegue y evidencias (A4)"),
    ("F2", "Diseños de referencia (anexo C: diseños 1 a 11)", "Cliente", "11 pantallas: acceso, recuperación, mantenedores e ingreso de atención"),
    ("F3", "Normas gráficas institucionales de la Municipalidad de La Serena", "Municipalidad", "Color Rojo Heráldico (HEX #C41230, Pantone 200 C), logotipo y usos permitidos"),
    ("F4", "Revisión del prototipo funcional con el cliente (pruebas de aceptación)", "Equipo + cliente", "71 pruebas funcionales y 12 pruebas de interfaz ejecutadas sobre el prototipo"),
]

# --------------------------------------------------------------------------
# Requerimientos funcionales: id, nombre, descripción, épica, fuente, prioridad (MoSCoW)
# --------------------------------------------------------------------------
RF = [
    ("RF01", "Iniciar sesión", "El sistema debe permitir el ingreso con nombre de usuario o correo y contraseña, validando credenciales, cuenta y rol activos.", "EP01", "F1", "Must"),
    ("RF02", "Bloquear por intentos fallidos", "El sistema debe bloquear temporalmente el acceso tras un número configurable de intentos fallidos.", "EP01", "F1", "Should"),
    ("RF03", "Cerrar sesión y proteger rutas", "El sistema debe cerrar la sesión y exigir autenticación en todas las rutas internas.", "EP01", "F1", "Must"),
    ("RF04", "Solicitar código de recuperación", "El sistema debe enviar un código de 6 dígitos al correo asociado, con un mensaje genérico que no revele si la cuenta existe.", "EP01", "F1", "Must"),
    ("RF05", "Validar código", "El sistema debe validar el código considerando vigencia, intentos fallidos, reenvío con espera y uso único.", "EP01", "F1/F2", "Must"),
    ("RF06", "Crear nueva contraseña", "El sistema debe permitir crear una nueva contraseña, solo tras una verificación válida, cumpliendo la política de claves.", "EP01", "F1/F2", "Must"),
    ("RF07", "Gestionar delegaciones", "El sistema debe permitir crear, consultar, listar, editar y eliminar o desactivar delegaciones (código, nombre, dirección, comuna, estado).", "EP02", "F1/F2", "Must"),
    ("RF08", "Gestionar roles y permisos", "El sistema debe administrar roles con su descripción, permisos por módulo y alcance autorizado.", "EP02", "F1/F2", "Must"),
    ("RF09", "Gestionar usuarios", "El sistema debe administrar usuarios con nombre, correo, rol, delegaciones autorizadas y estado.", "EP02", "F1/F2", "Must"),
    ("RF10", "Gestionar ítems y metas", "El sistema debe administrar ítems y metas (código, nombre, descripción, estado).", "EP03", "F1/F2", "Must"),
    ("RF11", "Gestionar tipos de atención", "El sistema debe administrar tipos de atención (código, nombre, descripción, estado).", "EP03", "F1/F2", "Must"),
    ("RF12", "Gestionar sub atenciones", "El sistema debe administrar sub atenciones asociadas a un tipo de atención, validando la integridad de la relación.", "EP03", "F1/F2", "Must"),
    ("RF13", "Buscar, filtrar y paginar", "Cada listado debe ofrecer búsqueda parcial en varios campos sin distinguir mayúsculas, filtros, paginador y total de resultados.", "EP05", "F1/F2", "Must"),
    ("RF14", "Exportar a Excel", "Cada listado debe exportar a Excel los resultados autorizados del filtro aplicado, sin contraseñas ni campos internos.", "EP05", "F1/F2", "Should"),
    ("RF15", "Identificar la delegación activa", "La cabecera debe mostrar la delegación activa, el usuario y su rol, y permitir cambiar entre delegaciones autorizadas.", "EP02", "F1/F2", "Must"),
    ("RF16", "Controlar el acceso por rol", "Cada usuario debe ver solo los menús y opciones autorizados por su rol; el servidor debe rechazar accesos no autorizados.", "EP02", "F1", "Must"),
    ("RF17", "Registrar atención ciudadana", "El sistema debe registrar atenciones con solicitante, tipo, sub atención dependiente, descripción, delegación, responsable y fecha automáticos.", "EP04", "F1/F2", "Must"),
    ("RF18", "Identificar o registrar vecino", "El formulario de atención debe buscar al vecino por RUT o nombre y permitir registrarlo si no existe.", "EP04", "F1/F2", "Must"),
    ("RF19", "Consultar atenciones", "El sistema debe listar y consultar las atenciones de la delegación activa con su folio.", "EP04", "F1", "Should"),
    ("RF20", "Plantillas de módulos futuros", "El sistema debe presentar plantillas navegables de Vecinos, Tipo de Gestión, Seguimiento, Reportes y Auditoría según el rol.", "EP06", "F1", "Could"),
]

RNF = [
    ("RNF01", "Seguridad", "Contraseñas almacenadas con hash (PBKDF2), protección CSRF, sesiones con expiración y cookies seguras con HTTPS.", "F1"),
    ("RNF02", "Seguridad", "Toda validación y control de permisos/delegación debe ejecutarse en el servidor; ocultar botones no constituye control de acceso.", "F1"),
    ("RNF03", "Privacidad", "La recuperación no debe revelar si un correo existe y las exportaciones no deben incluir contraseñas, tokens ni campos internos. Tratamiento conforme a la Ley N.º 19.628.", "F1"),
    ("RNF04", "Usabilidad", "Interfaz basada en las normas gráficas institucionales (Rojo Heráldico, logotipo) y un mismo template en todas las pantallas.", "F1/F3"),
    ("RNF05", "Usabilidad", "Alertas, confirmaciones y resultados de operación con SweetAlert2; nunca mostrar éxito si la operación falla.", "F1"),
    ("RNF06", "Accesibilidad", "El color no debe ser el único medio para identificar estados o contexto; controles accesibles por teclado.", "F1"),
    ("RNF07", "Portabilidad", "Diseño adaptable a escritorio, tablet y móvil (desde 390 px de ancho) en navegadores modernos.", "F1/F2"),
    ("RNF08", "Rendimiento", "Con 50 usuarios concurrentes, el percentil 95 de respuesta debe ser ≤ 1 s y la tasa de error ≤ 1 %.", "F1"),
    ("RNF09", "Disponibilidad", "El sistema debe estar desplegado en AWS con URL operativa y verificación de conexión a la base de datos.", "F1"),
    ("RNF10", "Mantenibilidad", "Código en repositorio Git remoto con historial, README, migraciones y configuración sin secretos.", "F1"),
    ("RNF11", "Compatibilidad", "Base de datos relacional MySQL/MariaDB con codificación utf8mb4.", "F1"),
    ("RNF12", "Calidad", "Toda función implementada debe estar probada: pruebas funcionales, de interfaz y de estrés con registro de resultados.", "F1"),
]

EPICAS = [
    ("EP01", "Acceso y seguridad", "Ingreso, cierre de sesión y recuperación de contraseña segura.", "RF01–RF06"),
    ("EP02", "Estructura municipal y permisos", "Delegaciones, roles, usuarios, contexto de delegación y control de acceso.", "RF07–RF09, RF15, RF16"),
    ("EP03", "Catálogos de atención", "Ítems y metas, tipos y sub atenciones.", "RF10–RF12"),
    ("EP04", "Atención ciudadana", "Registro y consulta de atenciones con su solicitante.", "RF17–RF19"),
    ("EP05", "Gestión de información", "Búsqueda, filtros, paginación y exportación de listados.", "RF13, RF14"),
    ("EP06", "Operación y evolución", "Despliegue en AWS y plantillas de módulos futuros.", "RF20, RNF09"),
]

# HU: id, épica, rol, quiero, para, SP, [ (tarea, horas) ], criterios de aceptación
HU = [
    ("HU01", "EP01", "usuario municipal", "ingresar con mi usuario o correo y contraseña", "acceder a los módulos de mi rol", 5,
     [("Diseñar pantalla de login con el template institucional", 3), ("Implementar autenticación por usuario o correo", 4),
      ("Bloqueo temporal por intentos fallidos", 3), ("Pruebas de ingreso correcto, incorrecto, vacío e inactivo", 3)],
     "Ingreso válido redirige al inicio; credenciales erróneas muestran mensaje genérico; cuenta inactiva rechazada."),
    ("HU02", "EP01", "usuario municipal", "recuperar mi contraseña mediante un código enviado a mi correo", "volver a ingresar sin depender de soporte", 8,
     [("Modelo de solicitud con código cifrado, vigencia e intentos", 3), ("Envío del código por SMTP", 3),
      ("Pantalla de código de 6 dígitos con temporizador y reenvío", 5), ("Pantalla de nueva contraseña con política visible", 3),
      ("Pruebas: código válido, incorrecto, vencido, reutilizado y reenvío", 5)],
     "Respuesta genérica; código de un solo uso; nueva clave solo tras verificación; la clave anterior deja de funcionar."),
    ("HU03", "EP01", "usuario municipal", "cerrar sesión y que las rutas internas exijan autenticación", "proteger la información", 2,
     [("Middleware de login requerido", 2), ("Cierre de sesión por POST", 1), ("Pruebas de rutas protegidas", 2)],
     "Sin sesión toda ruta interna redirige al login."),
    ("HU04", "EP02", "superadministrador", "gestionar las delegaciones municipales", "mantener actualizada la estructura territorial", 5,
     [("Modelo y migración de delegación", 2), ("Vistas de listar, crear, consultar, editar", 4),
      ("Regla de eliminación con relaciones / desactivación", 2), ("Pruebas del CRUD", 3)],
     "No se elimina una delegación con usuarios o atenciones; se ofrece desactivar."),
    ("HU05", "EP02", "superadministrador", "definir roles con permisos y alcance", "controlar qué puede hacer cada perfil", 8,
     [("Catálogo de módulos y acciones", 3), ("Matriz de permisos en el formulario", 4),
      ("Reglas: rol de sistema protegido y no escalar privilegios", 3), ("Pruebas de roles", 3)],
     "El rol Superadministrador no se elimina; nadie otorga permisos que no posee."),
    ("HU06", "EP02", "coordinador", "administrar usuarios de mis delegaciones", "asignar el personal de cada delegación", 8,
     [("Modelo de usuario con rol y delegaciones", 3), ("Formulario con validación de alcance y clave", 4),
      ("Alcance por delegación en listado y edición", 3), ("Pruebas de usuarios", 4)],
     "Correo y usuario únicos; un coordinador no asigna roles globales ni delegaciones ajenas."),
    ("HU07", "EP02", "coordinador", "ver y cambiar la delegación activa", "trabajar en el contexto correcto", 5,
     [("Middleware de contexto de delegación", 3), ("Distintivo en cabecera con selector", 3),
      ("Advertencia de cambios sin guardar", 2), ("Pruebas de cambio y manipulación de contexto", 3)],
     "Solo se listan delegaciones autorizadas; un cambio no autorizado responde 403."),
    ("HU08", "EP02", "usuario municipal", "ver solo los menús de mi rol", "no confundirme con opciones que no me corresponden", 3,
     [("Menú dinámico por permisos", 2), ("Decorador de permisos en servidor", 2), ("Pruebas de menú por rol", 3)],
     "Cada rol ve sus módulos; acceso por URL no autorizado responde 403."),
    ("HU09", "EP03", "delegado municipal", "gestionar ítems y metas", "registrar las metas del proyecto", 3,
     [("Modelo y CRUD de ítems", 3), ("Pruebas", 2)], "CRUD completo con validación de código único."),
    ("HU10", "EP03", "delegado municipal", "gestionar tipos de atención", "clasificar las atenciones", 3,
     [("Modelo y CRUD de tipos", 3), ("Regla de integridad con sub atenciones", 1), ("Pruebas", 2)],
     "No se elimina ni desactiva un tipo con sub atenciones activas."),
    ("HU11", "EP03", "delegado municipal", "gestionar sub atenciones asociadas a un tipo", "detallar la clasificación", 5,
     [("Modelo y CRUD de sub atenciones", 3), ("Validación de tipo activo y nombre único por tipo", 2),
      ("Bloqueo de cambio de tipo con atenciones", 1), ("Pruebas", 3)],
     "La sub atención muestra su tipo asociado; integridad validada antes de modificar."),
    ("HU12", "EP05", "usuario municipal", "buscar, filtrar y paginar los listados", "encontrar registros rápidamente", 5,
     [("Búsqueda parcial en varios campos", 3), ("Filtros combinables y paginador que conserva filtros", 3),
      ("Estados de carga, vacío y sin coincidencias", 2), ("Pruebas", 3)],
     "La búsqueda no distingue mayúsculas; los filtros se conservan al cambiar de página."),
    ("HU13", "EP04", "funcionario", "registrar una atención ciudadana", "dejar constancia de la solicitud del vecino", 8,
     [("Formulario de atención con dependencia tipo → sub atención", 5), ("Asignación de delegación, responsable y fecha", 2),
      ("Prevención de doble envío y folio", 3), ("Pruebas funcionales y de interfaz", 4)],
     "La sub atención muestra solo opciones activas del tipo; cancelar no crea registros; se muestra el folio."),
    ("HU14", "EP05", "coordinador", "exportar los listados a Excel", "analizar la información fuera del sistema", 3,
     [("Exportación con openpyxl del filtro completo", 3), ("Pruebas de coherencia tabla–archivo", 2)],
     "El archivo contiene todas las páginas del filtro y ningún dato sensible."),
    ("HU15", "EP04", "funcionario", "buscar o registrar al vecino solicitante", "identificar correctamente a quien solicita", 5,
     [("Búsqueda de vecino por RUT o nombre", 3), ("Registro de vecino con validación de RUT", 3), ("Pruebas", 2)],
     "RUT validado con dígito verificador; no se duplican vecinos."),
    ("HU16", "EP04", "delegado municipal", "consultar las atenciones de mi delegación", "supervisar el trabajo del equipo", 3,
     [("Listado y ficha de atención", 2), ("Alcance por delegación activa", 1), ("Pruebas", 2)],
     "Una atención de otra delegación no es accesible por URL."),
    ("HU17", "EP06", "usuario municipal", "navegar las plantillas de módulos futuros", "conocer la evolución del sistema", 3,
     [("Plantillas de Vecinos, Gestiones, Seguimiento, Reportes y Auditoría", 3), ("Control de acceso por rol", 1)],
     "Las plantillas informan «función pendiente» y no simulan éxito."),
    ("HU18", "EP06", "encargado TI municipal", "disponer del sistema en AWS", "que los funcionarios lo usen desde cualquier lugar", 5,
     [("Script de instalación en EC2 (nginx, gunicorn, MariaDB)", 5), ("Configuración de correo y secretos", 2),
      ("Pruebas de estrés con Locust", 4)],
     "URL operativa, base de datos conectada y prueba de estrés registrada."),
]

SPRINTS = [
    ("Sprint 0", "Preparación", "17/08 – 28/08", "Visión, backlog inicial, análisis documental, repositorio Git, entorno de desarrollo, arquitectura", "—"),
    ("Sprint 1", "Acceso seguro", "31/08 – 11/09", "HU01, HU02, HU03, HU08", "18"),
    ("Sprint 2", "Estructura municipal", "14/09 – 02/10", "HU04, HU05, HU06", "21"),
    ("Sprint 3", "Contexto y catálogos", "05/10 – 16/10", "HU07, HU09, HU10, HU11, HU12", "21"),
    ("Sprint 4", "Atención ciudadana", "19/10 – 30/10", "HU13, HU14, HU15, HU16", "19"),
    ("Sprint 5", "Despliegue y evolución", "02/11 – 13/11", "HU17, HU18, pruebas de estrés, correcciones y entrega", "8"),
]

AMBIGUEDADES = [
    ("Vigencia del código (10 min) y espera de reenvío (45 s)", "F1 los declara «valores referenciales»", "Se dejan configurables por variables de entorno con esos valores por defecto."),
    ("Catálogo de Vecinos", "F1 indica que es contexto y no requisito completo", "El vecino se identifica y registra desde el ingreso de atención; su mantenedor queda como plantilla."),
    ("Roles y permisos", "F1 entrega solo ejemplos de roles", "El equipo define 4 roles (Superadministrador, Coordinador, Delegado municipal, Funcionario) con matriz de permisos."),
    ("Tipografía institucional", "F3 no fue accesible durante el levantamiento", "Se adoptan Montserrat y Open Sans (licencia libre) como supuesto documentado, a validar con el cliente."),
    ("Usuario con varias delegaciones", "F1 exige selector solo con delegaciones autorizadas", "Se define el alcance del rol: global, varias delegaciones o una delegación (contexto fijo)."),
    ("Eliminar o desactivar", "F1 acepta ambas opciones", "Se elimina solo si no hay relaciones; en caso contrario se ofrece desactivar."),
]

COMPARACION = [  # criterio, peso, cascada, incremental, scrum
    ("Adaptación a cambios de requisitos", 25, 1, 3, 5),
    ("Entregas tempranas y validación con el cliente", 20, 1, 4, 5),
    ("Ajuste a un equipo pequeño (3 integrantes)", 15, 3, 4, 5),
    ("Ajuste al calendario académico por evaluaciones", 15, 2, 4, 4),
    ("Control de riesgos técnicos", 15, 2, 4, 4),
    ("Documentación formal requerida", 10, 5, 4, 3),
]

RECURSOS_SWHW = [
    ("Desarrollo", "Equipo de desarrollo", "CPU 4 núcleos, 8 GB RAM, 20 GB libres", "CPU 6+ núcleos, 16 GB RAM, SSD 256 GB"),
    ("Desarrollo", "Sistema operativo", "Windows 10, macOS 12 o Linux", "Windows 11 / Ubuntu 24.04"),
    ("Desarrollo", "Software", "Python 3.11, Git, editor de código, navegador, SQLite", "Python 3.13, VS Code, GitHub, MariaDB local, PlantUML, Playwright, Locust"),
    ("Operación", "Servidor de aplicación (AWS EC2)", "t3.micro: 2 vCPU, 1 GB RAM, 8 GB EBS", "t3.small: 2 vCPU, 2 GB RAM, 20 GB EBS gp3, IP elástica"),
    ("Operación", "Base de datos", "MariaDB 10.11 en la misma EC2", "Amazon RDS MySQL 8 db.t3.micro con respaldos automáticos"),
    ("Operación", "Software base", "Ubuntu 24.04, nginx, gunicorn, Django 5.2", "Igual al mínimo + certificado HTTPS (Let's Encrypt) y monitoreo CloudWatch"),
    ("Operación", "Correo", "Gmail SMTP con contraseña de aplicación", "Amazon SES con dominio verificado"),
    ("Operación", "Equipos de usuarios", "Navegador moderno, pantalla 1366×768 o móvil 390 px", "Navegador actualizado, pantalla Full HD, conexión 10 Mbps"),
    ("Arquitectura", "Estilo", "Monolito web Django por capas (MVT)", "Monolito modular con apps desacopladas, preparado para escalar horizontalmente detrás de un balanceador"),
]

RECURSOS_HUMANOS = [
    ("Desarrollo", "Integrante 1 (representante)", "Scrum Master e interlocutor con el docente; desarrollo backend", "10 h/semana"),
    ("Desarrollo", "Integrante 2", "Desarrollo frontend, template institucional y wireframes", "10 h/semana"),
    ("Desarrollo", "Integrante 3", "Pruebas (QA), despliegue AWS y documentación", "10 h/semana"),
    ("Desarrollo", "Docente / Municipalidad", "Product Owner (cliente): prioriza y valida", "Revisión al cierre de cada sprint"),
    ("Operación", "Administrador de sistemas TI", "Mantención de la EC2, respaldos y actualizaciones", "4 h/semana"),
    ("Operación", "Administrador funcional (Superadministrador)", "Usuarios, roles, delegaciones y catálogos", "2 h/semana"),
    ("Operación", "Mesa de ayuda municipal", "Soporte de primer nivel a funcionarios", "Según demanda"),
]

GLOSARIO = [
    ("AWS EC2", "Servicio de Amazon Web Services que provee servidores virtuales en la nube."),
    ("Backlog", "Lista priorizada de historias de usuario pendientes del producto (Product Backlog) o del sprint (Sprint Backlog)."),
    ("Caso de uso", "Descripción de la interacción entre un actor y el sistema para lograr un objetivo."),
    ("CRUD", "Operaciones básicas de un mantenedor: crear, leer (consultar), actualizar y eliminar."),
    ("CSRF", "Ataque que fuerza a un usuario autenticado a ejecutar acciones no deseadas; se mitiga con tokens."),
    ("Delegación", "Unidad territorial de la Municipalidad de La Serena que atiende a los vecinos de un sector."),
    ("Django", "Framework web de Python basado en el patrón Modelo-Vista-Plantilla (MVT)."),
    ("Épica", "Requerimiento de gran tamaño que agrupa varias historias de usuario."),
    ("Historia de usuario (HU)", "Requerimiento expresado desde la perspectiva del usuario: «Como… quiero… para…»."),
    ("MoSCoW", "Técnica de priorización: Must, Should, Could y Won't."),
    ("Mantenedor", "Pantalla de administración de un catálogo o entidad del sistema."),
    ("Prototipo", "Versión funcional temprana del sistema usada para validar requerimientos con el cliente."),
    ("Punto de historia (SP)", "Unidad relativa de esfuerzo para estimar historias de usuario (escala de Fibonacci)."),
    ("RF / RNF", "Requerimiento funcional (qué hace el sistema) y no funcional (cómo debe hacerlo: calidad, seguridad, rendimiento)."),
    ("Scrum", "Marco de trabajo ágil iterativo e incremental basado en sprints, roles y eventos definidos."),
    ("SMTP", "Protocolo estándar para el envío de correo electrónico."),
    ("Sprint", "Iteración de duración fija (dos semanas en este proyecto) que produce un incremento usable."),
    ("SweetAlert2", "Biblioteca JavaScript para mostrar alertas y confirmaciones accesibles y personalizables."),
    ("UML", "Lenguaje Unificado de Modelado, estándar para especificar y documentar sistemas de software."),
    ("Wireframe", "Esquema visual de baja fidelidad que representa la estructura de una pantalla."),
]

REFERENCIAS = [
    ("Amazon Web Services. (2026). ", "Amazon EC2 User Guide", ". Recuperado de https://docs.aws.amazon.com/ec2/"),
    ("Booch, G., Rumbaugh, J. y Jacobson, I. (2006). ", "El lenguaje unificado de modelado: Guía del usuario", " (2.ª ed.). Madrid: Pearson Educación."),
    ("Cohn, M. (2004). ", "User stories applied: For agile software development", ". Boston: Addison-Wesley."),
    ("Django Software Foundation. (2025). ", "Django documentation (versión 5.2)", ". Recuperado de https://docs.djangoproject.com/en/5.2/"),
    ("Jones, C. (2011). ", "Estimación de costos y administración de proyectos de software", ". México: McGraw Hill Interamericana."),
    ("Ley N.º 19.628. Sobre protección de la vida privada. ", "Diario Oficial de la República de Chile", ", 28 de agosto de 1999."),
    ("Pressman, R. (2010). ", "Ingeniería del software: Un enfoque práctico", " (7.ª ed.). España: McGraw Hill Interamericana."),
    ("Schwaber, K. y Sutherland, J. (2020). ", "La Guía Scrum", ". Recuperado de https://scrumguides.org/"),
    ("Sommerville, I. (2011). ", "Ingeniería de software", " (9.ª ed.). México: Pearson Educación."),
    ("Wiegers, K. y Beatty, J. (2013). ", "Software requirements", " (3.ª ed.). Redmond: Microsoft Press."),
]
