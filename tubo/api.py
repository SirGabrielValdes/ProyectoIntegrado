"""
API REST v1 para la App Móvil (documentada en docs/api_movil.md).

Autenticación: POST /api/v1/token/ con usuario o correo y clave entrega un token;
las demás rutas exigen la cabecera «Authorization: Token <token>».
"""
import json
from functools import wraps

from django.contrib.auth.decorators import login_not_required
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.urls import path, reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from cuentas.backends import buscar_por_identificador

from . import servicios
from .models import Compromiso, TokenApi

MAX_INTENTOS = 5


def error(mensaje, estado):
    return JsonResponse({"error": mensaje}, status=estado)


def con_token(permiso):
    def decorador(vista):
        @csrf_exempt
        @login_not_required
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            cabecera = request.headers.get("Authorization", "")
            tipo, _, clave = cabecera.partition(" ")
            token = TokenApi.validar(clave.strip()) if tipo == "Token" else None
            if token is None:
                return error("Token ausente, inválido o vencido.", 401)
            usuario = token.usuario
            if not usuario.is_active or not usuario.rol.activo or usuario.debe_cambiar_clave:
                return error("La cuenta no está habilitada para usar la API.", 403)
            if not usuario.tiene_permiso(permiso):
                return error("Sin permiso para esta operación.", 403)
            request.usuario_api = usuario
            return vista(request, *args, **kwargs)
        return envoltura
    return decorador


def _compromisos(usuario):
    delegaciones = [d.pk for d in usuario.delegaciones_autorizadas()]
    return Compromiso.objects.select_related("responsable", "area_apoyo", "actividad", "atencion").filter(
        delegacion_id__in=delegaciones)


def _json(c, detalle=False):
    datos = {
        "id": c.pk, "codigo": c.codigo, "referencia": c.referencia, "titulo": c.titulo,
        "solicitante": c.solicitante, "estado": c.estado, "estado_texto": c.estado_texto,
        "responsable": c.responsable.nombre, "area_apoyo": c.area_apoyo.nombre if c.area_apoyo else None,
        "delegacion": c.delegacion.codigo, "creado": c.creado.isoformat(),
    }
    if detalle:
        datos["descripcion"] = c.descripcion
        datos["evidencias"] = [{
            "id": e.pk, "estado": e.estado, "descripcion": e.descripcion, "origen": e.origen,
            "subida_en": e.subida_en.isoformat(), "comentario_revision": e.comentario_revision,
        } for e in c.evidencias.all()]
    return datos


@csrf_exempt
@login_not_required
@require_http_methods(["POST"])
def emitir_token(request):
    try:
        datos = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        datos = request.POST
    identificador, clave = (datos.get("identificador") or "").strip(), datos.get("clave") or ""
    if not identificador or not clave:
        return error("Indique identificador y clave.", 400)
    intentos_clave = "api-intentos:" + identificador.lower()[:120]
    if cache.get(intentos_clave, 0) >= MAX_INTENTOS:
        return error("Demasiados intentos fallidos. Espere unos minutos.", 429)
    usuario = buscar_por_identificador(identificador)
    if not usuario or not usuario.check_password(clave):
        cache.set(intentos_clave, cache.get(intentos_clave, 0) + 1, 300)
        return error("Credenciales incorrectas.", 401)
    if not usuario.is_active or not usuario.rol.activo:
        return error("La cuenta está inactiva.", 403)
    if usuario.debe_cambiar_clave:
        return error("Debe cambiar su clave provisoria en el sitio web antes de usar la app.", 403)
    cache.delete(intentos_clave)
    token, clave_token = TokenApi.emitir(usuario)
    return JsonResponse({"token": clave_token, "expira": token.expira.isoformat(),
                         "usuario": {"nombre": usuario.nombre, "rol": usuario.rol.nombre}}, status=201)


@con_token("tubo.ver")
@require_http_methods(["GET"])
def listar_compromisos(request):
    qs = _compromisos(request.usuario_api)
    if request.GET.get("asignados") == "1":
        qs = qs.filter(responsable=request.usuario_api)
    if request.GET.get("estado"):
        qs = qs.filter(estado=request.GET["estado"])
    return JsonResponse({"resultados": [_json(c) for c in qs[:200]]})


@con_token("tubo.ver")
@require_http_methods(["GET"])
def ver_compromiso(request, pk):
    c = _compromisos(request.usuario_api).filter(pk=pk).first()
    if c is None:
        return error("Compromiso no encontrado o fuera de su alcance.", 404)
    return JsonResponse(_json(c, detalle=True))


@con_token("tubo.editar")
@require_http_methods(["POST"])
def subir_evidencia(request, pk):
    c = _compromisos(request.usuario_api).filter(pk=pk).first()
    if c is None:
        return error("Compromiso no encontrado o fuera de su alcance.", 404)
    try:
        e = servicios.subir_evidencia(c, request.usuario_api, request.FILES.get("foto"),
                                      request.POST.get("descripcion", ""), origen="APP")
    except ValidationError as ex:
        return error(" ".join(ex.messages), 400)
    return JsonResponse({"id": e.pk, "estado": e.estado,
                         "mensaje": "Evidencia recibida; queda pendiente de revisión del delegado.",
                         "compromiso": reverse("api:compromiso", args=[c.pk])}, status=201)


urlpatterns = ([
    path("token/", emitir_token, name="token"),
    path("compromisos/", listar_compromisos, name="compromisos"),
    path("compromisos/<int:pk>/", ver_compromiso, name="compromiso"),
    path("compromisos/<int:pk>/evidencias/", subir_evidencia, name="evidencias"),
], "api")
