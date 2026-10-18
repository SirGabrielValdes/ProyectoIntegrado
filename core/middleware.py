from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect

CLAVE_SESION = "delegacion_activa_id"


class ContextoDelegacionMiddleware:
    """
    Determina en el servidor la delegación activa del usuario.

    La delegación activa siempre se toma de la sesión y se valida contra las
    delegaciones autorizadas del perfil; nunca de un parámetro del navegador.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.delegacion_activa = None
        request.delegaciones_autorizadas = []
        usuario = getattr(request, "user", None)
        if usuario is not None and usuario.is_authenticated:
            autorizadas = list(usuario.delegaciones_autorizadas().order_by("codigo"))
            if not autorizadas:
                logout(request)
                messages.error(
                    request,
                    "Su cuenta no tiene una delegación activa asignada. Contacte al administrador.",
                )
                return redirect("cuentas:login")
            activa_id = request.session.get(CLAVE_SESION)
            activa = next((d for d in autorizadas if d.pk == activa_id), autorizadas[0])
            request.session[CLAVE_SESION] = activa.pk
            request.delegacion_activa = activa
            request.delegaciones_autorizadas = autorizadas
        return self.get_response(request)
