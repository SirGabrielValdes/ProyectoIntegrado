from django.contrib import messages
from django.contrib.auth.decorators import login_not_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import Resolver404, resolve, reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from catalogos.models import Delegacion, Item, SubAtencion, TipoAtencion
from cuentas.models import Rol, Usuario

from .middleware import CLAVE_SESION
from .permisos import ACCIONES, ESTADO_MODULO, MODULOS, NOMBRE_MODULO

PENDIENTES = {
    "vecinos": {
        "descripcion": "Registro y consulta de vecinos solicitantes (RUT, contacto, dirección e historial de atenciones).",
        "columnas": ["RUT", "Nombre", "Teléfono", "Sector", "Atenciones"],
        "filas": [["11.111.111-1", "Vecina de ejemplo", "+56 9 1111 1111", "Centro", "3"],
                  ["22.222.222-2", "Vecino de ejemplo", "+56 9 2222 2222", "Las Compañías", "1"]],
    },
    "gestiones": {
        "descripcion": "Catálogo de tipos de gestión aplicables al seguimiento de cada atención.",
        "columnas": ["Código", "Nombre", "Plazo (días)", "Estado"],
        "filas": [["GES01", "Derivación interna", "5", "Activo"], ["GES02", "Visita a terreno", "10", "Activo"]],
    },
    "seguimiento": {
        "descripcion": "Seguimiento del ciclo de vida de las atenciones: derivaciones, gestiones y cierre.",
        "columnas": ["Folio", "Vecino", "Gestión", "Estado", "Plazo"],
        "filas": [["AT-2026-000001", "Vecina de ejemplo", "Derivación interna", "En curso", "3 días"],
                  ["AT-2026-000002", "Vecino de ejemplo", "Visita a terreno", "Pendiente", "8 días"]],
    },
    "reportes": {
        "descripcion": "Reportes de gestión por delegación, tipo de atención y período.",
        "columnas": ["Reporte", "Período", "Delegación", "Formato"],
        "filas": [["Atenciones por tipo", "Mensual", "Delegación activa", "Excel / PDF"],
                  ["Tiempos de respuesta", "Trimestral", "Delegación activa", "Excel"]],
    },
    "auditoria": {
        "descripcion": "Registro de auditoría: accesos, cambios en mantenedores y operaciones sensibles.",
        "columnas": ["Fecha", "Usuario", "Acción", "Módulo", "Detalle"],
        "filas": [["01-10-2026 09:00", "usuario.ejemplo", "Ingreso", "Acceso", "Inicio de sesión"],
                  ["01-10-2026 09:05", "usuario.ejemplo", "Edición", "Usuarios", "Cambio de rol"]],
    },
}


def inicio(request):
    u = request.user
    activa = request.delegacion_activa
    tarjetas = []

    def tarjeta(modulo, titulo, valor, detalle, url_name):
        if u.tiene_permiso(f"{modulo}.ver"):
            tarjetas.append({"titulo": titulo, "valor": valor, "detalle": detalle, "url": reverse(url_name)})

    if u.tiene_permiso("atenciones.ver"):
        from atenciones.views import atenciones as m_atenciones

        visibles = m_atenciones.queryset(request)
        hoy = visibles.filter(fecha_registro__date=timezone.localdate()).count()
        tarjeta("atenciones", "Atenciones", visibles.count(), f"{hoy} registradas hoy en {activa.codigo}",
                "atenciones:lista")
    if u.tiene_permiso("delegaciones.ver"):
        n = Delegacion.objects.count() if u.rol.es_global else u.delegaciones.count()
        tarjeta("delegaciones", "Delegaciones", n, "En su alcance autorizado", "delegaciones:lista")
    if u.tiene_permiso("usuarios.ver"):
        from cuentas.views import usuarios as m_usuarios

        tarjeta("usuarios", "Usuarios", m_usuarios.queryset(request).filter(delegaciones=activa).count(),
                f"Asignados a {activa.codigo}", "usuarios:lista")
    tarjeta("roles", "Roles", Rol.objects.filter(activo=True).count(), "Roles activos", "roles:lista")
    tarjeta("items", "Ítems y metas", Item.objects.filter(activo=True).count(), "Ítems activos", "items:lista")
    tarjeta("tipos", "Tipos de Atención", TipoAtencion.objects.filter(activo=True).count(), "Tipos activos",
            "tipos:lista")
    tarjeta("subatenciones", "Sub Atenciones", SubAtencion.objects.filter(activo=True).count(),
            "Sub atenciones activas", "subatenciones:lista")

    permisos = []
    for codigo, nombre, acciones, estado in MODULOS:
        concedidas = [ACCIONES[a] for a in acciones if u.tiene_permiso(f"{codigo}.{a}")]
        if concedidas:
            permisos.append({"modulo": nombre, "acciones": concedidas, "estado": estado})
    return render(request, "core/inicio.html", {
        "tarjetas": tarjetas,
        "permisos_usuario": permisos,
        "puede_ingresar_atencion": u.tiene_permiso("atenciones.crear"),
        "total_usuarios": Usuario.objects.count() if u.rol.es_global else None,
    })


@require_POST
def cambiar_delegacion(request):
    destino_id = request.POST.get("delegacion", "")
    autorizadas = {str(d.pk): d for d in request.delegaciones_autorizadas}
    if destino_id not in autorizadas:
        # Intento de usar una delegación no autorizada: se rechaza en el servidor.
        raise PermissionDenied("Delegación no autorizada para su perfil.")
    nueva = autorizadas[destino_id]
    request.session[CLAVE_SESION] = nueva.pk
    messages.success(request, f"Contexto cambiado a {nueva.codigo} · {nueva.nombre}.")
    # Se vuelve al listado del módulo: formularios y fichas pertenecen al contexto anterior.
    siguiente = request.POST.get("siguiente", "")
    try:
        coincidencia = resolve(siguiente)
        if coincidencia.namespace and coincidencia.namespace not in ("core", "cuentas"):
            return redirect(f"{coincidencia.namespace}:lista")
        if coincidencia.view_name == "core:pendiente":
            return redirect(siguiente)
    except Resolver404:
        pass
    return redirect("core:inicio")


def pendiente(request, modulo):
    if ESTADO_MODULO.get(modulo) != "pendiente":
        raise Http404
    if not request.user.tiene_permiso(f"{modulo}.ver"):
        raise PermissionDenied
    return render(request, "core/pendiente.html", {
        "modulo": modulo, "titulo": NOMBRE_MODULO[modulo], **PENDIENTES[modulo]})


@login_not_required
def error_403(request, exception=None):
    return render(request, "errores/403.html", status=403)


@login_not_required
def error_404(request, exception=None):
    return render(request, "errores/404.html", status=404)


@login_not_required
def error_500(request):
    return render(request, "errores/500.html", status=500)


@login_not_required
def salud(request):
    from django.db import connection
    from django.http import JsonResponse

    with connection.cursor() as c:
        c.execute("SELECT 1")
    return JsonResponse({"estado": "ok"})

