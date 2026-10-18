from django.conf import settings
from django.urls import reverse

from .permisos import ESTADO_MODULO

# Menú lateral: (módulo de permiso, etiqueta, nombre de URL, icono)
MENU = [
    ("inicio", "Inicio", "core:inicio", "inicio"),
    ("delegaciones", "Delegaciones", "delegaciones:lista", "edificio"),
    ("roles", "Roles", "roles:lista", "escudo"),
    ("usuarios", "Usuarios", "usuarios:lista", "personas"),
    ("items", "Ítems y metas", "items:lista", "meta"),
    ("tipos", "Tipo de Atención", "tipos:lista", "carpeta"),
    ("subatenciones", "Sub Atención", "subatenciones:lista", "lista"),
    ("atenciones", "Atenciones", "atenciones:lista", "chat"),
    ("vecinos", "Vecinos", "core:pendiente", "persona"),
    ("gestiones", "Tipo de Gestión", "core:pendiente", "engranaje"),
    ("seguimiento", "Seguimiento", "core:pendiente", "reloj"),
    ("reportes", "Reportes", "core:pendiente", "grafico"),
    ("auditoria", "Auditoría", "core:pendiente", "lupa"),
]


def sgr(request):
    contexto = {"VERSION_SGR": settings.VERSION_SGR}
    usuario = getattr(request, "user", None)
    if not (usuario and usuario.is_authenticated):
        return contexto

    rm = getattr(request, "resolver_match", None)
    if rm and rm.view_name == "core:pendiente":
        seccion = rm.kwargs.get("modulo")
    elif rm and rm.namespace and rm.namespace != "core":
        seccion = rm.namespace
    else:
        seccion = "inicio"
    menu = []
    for modulo, etiqueta, url_name, icono in MENU:
        if not usuario.tiene_permiso(f"{modulo}.ver"):
            continue
        url = reverse(url_name, args=[modulo]) if url_name == "core:pendiente" else reverse(url_name)
        menu.append({
            "modulo": modulo,
            "etiqueta": etiqueta,
            "url": url,
            "icono": icono,
            "pendiente": ESTADO_MODULO.get(modulo) == "pendiente",
            "actual": modulo == seccion,
        })
    contexto.update({
        "menu": menu,
        "delegacion_activa": getattr(request, "delegacion_activa", None),
        "delegaciones_autorizadas": getattr(request, "delegaciones_autorizadas", []),
        "puede": PermisosPlantilla(usuario),
    })
    return contexto


class PermisosPlantilla:
    """Permite escribir {% if puede.usuarios_crear %} en las plantillas."""

    def __init__(self, usuario):
        self.usuario = usuario

    def __getitem__(self, clave):
        return self.usuario.tiene_permiso(clave.replace("_", ".", 1))

    def __getattr__(self, clave):
        if clave.startswith("__"):
            raise AttributeError(clave)
        return self[clave]
