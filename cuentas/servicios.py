"""Clave provisoria de usuarios nuevos: generación y envío por correo."""
import logging
import secrets
import string

from django.core.mail import send_mail
from django.urls import reverse

from .validadores import requisitos_incumplidos

log = logging.getLogger("sgr")


def generar_clave_provisoria():
    """Clave aleatoria de 11 caracteres que cumple la política de contraseñas."""
    alfabeto = string.ascii_letters + string.digits
    while True:
        base = "".join(secrets.choice(alfabeto) for _ in range(10))
        clave = f"{base[:5]}-{base[5:]}"
        if not requisitos_incumplidos(clave):
            return clave


def enviar_clave_provisoria(usuario, clave, request=None):
    """Envía la clave provisoria al correo del usuario. Devuelve True si se envió."""
    url = request.build_absolute_uri(reverse("cuentas:login")) if request else ""
    try:
        send_mail(
            "SGR La Serena · Su cuenta y clave provisoria",
            f"Hola {usuario.nombre}:\n\n"
            "Se creó su cuenta en el Sistema de Gestión de Requerimientos (SGR) de la Municipalidad de La Serena.\n\n"
            f"Usuario: {usuario.username}\n"
            f"Clave provisoria: {clave}\n"
            f"{'Ingreso: ' + url if url else ''}\n\n"
            "Por seguridad, el sistema le pedirá cambiar esta clave en su primer ingreso.\n"
            "Si usted no esperaba este correo, ignórelo o informe al administrador del sistema.\n\n"
            "Sistema de Gestión de Requerimientos · Ilustre Municipalidad de La Serena",
            None, [usuario.correo],
        )
        return True
    except Exception:  # noqa: BLE001 - se informa al administrador sin exponer la clave
        log.exception("No fue posible enviar la clave provisoria al usuario %s", usuario.pk)
        return False
