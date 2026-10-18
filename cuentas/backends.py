from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

from .models import Usuario


def buscar_por_identificador(identificador):
    """Busca un usuario por nombre de usuario o correo (sin distinguir mayúsculas)."""
    identificador = (identificador or "").strip()
    if not identificador:
        return None
    return (
        Usuario.objects.select_related("rol")
        .filter(Q(username__iexact=identificador) | Q(correo__iexact=identificador))
        .first()
    )


class UsuarioOCorreoBackend(ModelBackend):
    """Permite ingresar con usuario o correo. Solo autentica cuentas activas con rol activo."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        usuario = buscar_por_identificador(username)
        if usuario is None:
            # Igualar el tiempo de respuesta para no revelar si la cuenta existe.
            Usuario().set_password(password)
            return None
        if usuario.check_password(password) and self.user_can_authenticate(usuario):
            return usuario
        return None

    def user_can_authenticate(self, user):
        return user.is_active and user.rol.activo

    def get_user(self, user_id):
        usuario = Usuario.objects.select_related("rol").filter(pk=user_id).first()
        return usuario if usuario and self.user_can_authenticate(usuario) else None
