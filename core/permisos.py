"""
Catálogo de módulos y permisos del SGR.

Cada permiso es un código "<modulo>.<accion>" que se guarda en Rol.permisos.
El menú, los botones y —sobre todo— las vistas del servidor consultan este
catálogo. Ocultar un botón no es control de acceso: cada vista valida el
permiso con @requiere_permiso.
"""
from functools import wraps

from django.core.exceptions import PermissionDenied

ACCIONES = {
    "ver": "Ver / listar",
    "crear": "Crear",
    "editar": "Editar",
    "eliminar": "Eliminar / desactivar",
    "exportar": "Exportar a Excel",
}

# (código, nombre, acciones disponibles, estado del módulo en esta entrega)
MODULOS = [
    ("inicio", "Inicio", ["ver"], "operativo"),
    ("delegaciones", "Delegaciones", ["ver", "crear", "editar", "eliminar", "exportar"], "operativo"),
    ("roles", "Roles y permisos", ["ver", "crear", "editar", "eliminar", "exportar"], "operativo"),
    ("usuarios", "Usuarios", ["ver", "crear", "editar", "eliminar", "exportar"], "operativo"),
    ("items", "Ítems y metas", ["ver", "crear", "editar", "eliminar", "exportar"], "operativo"),
    ("tipos", "Tipo de Atención", ["ver", "crear", "editar", "eliminar", "exportar"], "operativo"),
    ("subatenciones", "Sub Atención", ["ver", "crear", "editar", "eliminar", "exportar"], "operativo"),
    ("atenciones", "Atenciones", ["ver", "crear", "exportar"], "operativo"),
    ("vecinos", "Vecinos", ["ver"], "pendiente"),
    ("gestiones", "Tipo de Gestión", ["ver"], "pendiente"),
    ("seguimiento", "Seguimiento", ["ver"], "pendiente"),
    ("reportes", "Reportes", ["ver"], "pendiente"),
    ("auditoria", "Auditoría", ["ver"], "pendiente"),
]

NOMBRE_MODULO = {m[0]: m[1] for m in MODULOS}
ESTADO_MODULO = {m[0]: m[3] for m in MODULOS}
TODOS_LOS_PERMISOS = [f"{m[0]}.{a}" for m in MODULOS for a in m[2]]


def _mod(modulo, *acciones):
    return [f"{modulo}.{a}" for a in acciones]


CRUD = ("ver", "crear", "editar", "eliminar", "exportar")

# Definición de roles del equipo (se cargan con `manage.py cargar_datos_demo`
# y pueden modificarse desde el mantenedor de Roles).
ROLES_BASE = {
    "SUPERADMIN": {
        "codigo": "ROL01",
        "nombre": "Superadministrador",
        "descripcion": "Administra todo el sistema, todas las delegaciones y la configuración de seguridad.",
        "alcance": "GLOBAL",
        "es_sistema": True,
        "permisos": list(TODOS_LOS_PERMISOS),
    },
    "COORDINADOR": {
        "codigo": "ROL02",
        "nombre": "Coordinador",
        "descripcion": "Coordina varias delegaciones: administra usuarios de sus delegaciones y los catálogos de atención.",
        "alcance": "MULTIPLE",
        "es_sistema": False,
        "permisos": (
            ["inicio.ver", "delegaciones.ver", "delegaciones.exportar", "roles.ver"]
            + _mod("usuarios", *CRUD)
            + _mod("items", *CRUD)
            + _mod("tipos", *CRUD)
            + _mod("subatenciones", *CRUD)
            + _mod("atenciones", "ver", "crear", "exportar")
            + ["vecinos.ver", "gestiones.ver", "seguimiento.ver", "reportes.ver"]
        ),
    },
    "DELEGADO": {
        "codigo": "ROL03",
        "nombre": "Delegado municipal",
        "descripcion": "Responsable de una delegación: consulta su equipo y catálogos, registra y supervisa atenciones.",
        "alcance": "DELEGACION",
        "es_sistema": False,
        "permisos": (
            ["inicio.ver", "delegaciones.ver", "usuarios.ver", "usuarios.exportar",
             "items.ver", "items.exportar", "tipos.ver", "subatenciones.ver"]
            + _mod("atenciones", "ver", "crear", "exportar")
            + ["vecinos.ver", "seguimiento.ver", "reportes.ver"]
        ),
    },
    "FUNCIONARIO": {
        "codigo": "ROL04",
        "nombre": "Funcionario",
        "descripcion": "Operador de atención ciudadana en su delegación: registra y consulta atenciones.",
        "alcance": "DELEGACION",
        "es_sistema": False,
        "permisos": ["inicio.ver", "atenciones.ver", "atenciones.crear", "vecinos.ver"],
    },
}


def tiene_permiso(usuario, codigo):
    if not getattr(usuario, "is_authenticated", False):
        return False
    return usuario.tiene_permiso(codigo)


def requiere_permiso(*codigos):
    """Exige que el usuario tenga TODOS los permisos indicados (validación en servidor)."""

    def decorador(vista):
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            for codigo in codigos:
                if not tiene_permiso(request.user, codigo):
                    raise PermissionDenied(f"Sin permiso: {codigo}")
            return vista(request, *args, **kwargs)

        return envoltura

    return decorador
