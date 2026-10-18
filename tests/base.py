"""
Base de las pruebas funcionales.

Cada prueba documenta en su docstring, separado por «|»:
    Requisito | Módulo | Precondiciones | Pasos | Resultado esperado
El script pruebas/generar_matriz.py usa ese texto para construir la matriz
de pruebas funcionales (requisito, módulo, precondiciones, pasos, esperado,
obtenido, estado, evidencia, responsable y fecha).
"""
from django.contrib.messages import get_messages
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings

from catalogos.models import Delegacion
from cuentas.models import Usuario

CLAVE = "Serena.2026"


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
class PruebaSGR(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("cargar_datos_demo", atenciones=0, vecinos=5, stdout=open("/dev/null", "w"))
        cls.del01 = Delegacion.objects.get(codigo="DEL01")
        cls.del02 = Delegacion.objects.get(codigo="DEL02")
        cls.del04 = Delegacion.objects.get(codigo="DEL04")

    def setUp(self):
        cache.clear()

    def entrar(self, username):
        r = self.client.post("/cuenta/ingresar/", {"identificador": username, "clave": CLAVE})
        self.assertEqual(r.status_code, 302, f"No se pudo ingresar como {username}")
        self.client.get("/")  # consume el mensaje de bienvenida
        return Usuario.objects.get(username=username)

    def mensajes(self, respuesta):
        return [(m.level_tag, str(m)) for m in get_messages(respuesta.wsgi_request)]

    def assertMensaje(self, respuesta, nivel, contiene=""):
        msgs = self.mensajes(respuesta)
        self.assertTrue(any(n == nivel and contiene in t for n, t in msgs),
                        f"No se encontró mensaje {nivel!r} con {contiene!r}. Mensajes: {msgs}")

    def assertSinExito(self, respuesta):
        self.assertFalse(any(n == "success" for n, _ in self.mensajes(respuesta)),
                         "Se mostró un mensaje de éxito cuando la operación no debía completarse.")
