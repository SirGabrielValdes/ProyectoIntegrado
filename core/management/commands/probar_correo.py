"""
Envía un correo de prueba con la configuración SMTP del .env.

    python manage.py probar_correo destino@ejemplo.cl
"""
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Envía un correo de prueba para verificar la configuración SMTP."

    def add_arguments(self, parser):
        parser.add_argument("destino")

    def handle(self, *args, **opciones):
        if not settings.EMAIL_HOST:
            raise CommandError("EMAIL_HOST no está configurado: los correos solo se muestran en el log del servidor.")
        try:
            send_mail("SGR La Serena · Correo de prueba",
                      "La configuración de correo del SGR funciona. Aquí llegarán los códigos de recuperación.",
                      None, [opciones["destino"]])
        except Exception as e:  # noqa: BLE001
            raise CommandError(f"No se pudo enviar el correo ({type(e).__name__}): {e}")
        self.stdout.write(self.style.SUCCESS(f"Correo de prueba enviado a {opciones['destino']} "
                                             f"vía {settings.EMAIL_HOST}."))
