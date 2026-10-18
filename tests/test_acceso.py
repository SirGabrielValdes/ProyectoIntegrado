from django.core import mail
from django.test import override_settings
from django.utils import timezone
from datetime import timedelta

from cuentas.models import Rol, SolicitudRecuperacion, Usuario

from .base import CLAVE, PruebaSGR

NUEVA = "Nueva#Clave2026"


class LoginTests(PruebaSGR):
    def test_login_correcto_usuario(self):
        """A1-Login | Login | Usuario «funcionario» activo | Ingresar usuario y contraseña válidos | Redirige al inicio con sesión iniciada y delegación activa DEL01"""
        r = self.client.post("/cuenta/ingresar/", {"identificador": "funcionario", "clave": CLAVE})
        self.assertRedirects(r, "/")
        r = self.client.get("/")
        self.assertContains(r, "DEL01")
        self.assertContains(r, "Fernanda Funcionaria")

    def test_login_correcto_correo_sin_mayusculas(self):
        """A1-Login | Login | Usuario con correo funcionario@sgr.test | Ingresar el correo en mayúsculas y la contraseña | Ingreso aceptado (correo sin distinguir mayúsculas)"""
        r = self.client.post("/cuenta/ingresar/", {"identificador": "FUNCIONARIO@SGR.TEST", "clave": CLAVE})
        self.assertRedirects(r, "/")

    def test_login_incorrecto_mensaje_generico(self):
        """A3-Acceso | Login | Usuario existente | Ingresar contraseña errónea y luego un usuario inexistente | Mismo mensaje genérico en ambos casos, sin sesión"""
        r1 = self.client.post("/cuenta/ingresar/", {"identificador": "funcionario", "clave": "Mala.123"})
        r2 = self.client.post("/cuenta/ingresar/", {"identificador": "noexiste", "clave": "Mala.123"})
        for r in (r1, r2):
            self.assertEqual(r.status_code, 200)
            self.assertContains(r, "Usuario/correo o contraseña incorrectos")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_campos_vacios(self):
        """A3-Acceso | Login | Ninguna | Enviar el formulario sin datos | Se informan ambos campos obligatorios y no se inicia sesión"""
        r = self.client.post("/cuenta/ingresar/", {"identificador": "", "clave": ""})
        self.assertContains(r, "Ingrese su usuario o correo.")
        self.assertContains(r, "Ingrese su contraseña.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_cuenta_inactiva(self):
        """A3-Acceso | Login | Usuario «inactivo» con estado Inactivo | Ingresar credenciales correctas | Se rechaza el acceso indicando cuenta inactiva"""
        r = self.client.post("/cuenta/ingresar/", {"identificador": "inactivo", "clave": CLAVE})
        self.assertContains(r, "Su cuenta está inactiva")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_rol_inactivo(self):
        """A3-Acceso | Login | Rol Funcionario desactivado | Ingresar con un funcionario | Se rechaza el acceso por rol inactivo"""
        Rol.objects.filter(nombre="Funcionario").update(activo=False)
        r = self.client.post("/cuenta/ingresar/", {"identificador": "funcionario", "clave": CLAVE})
        self.assertContains(r, "Su rol está inactivo")

    @override_settings(LOGIN_MAX_INTENTOS=3)
    def test_login_bloqueo_por_intentos(self):
        """A3-Acceso | Login | Límite configurado en 3 intentos | Fallar 3 veces y luego usar la clave correcta | Bloqueo temporal: la clave correcta también se rechaza"""
        for _ in range(3):
            self.client.post("/cuenta/ingresar/", {"identificador": "funcionario", "clave": "Mala.123"})
        r = self.client.post("/cuenta/ingresar/", {"identificador": "funcionario", "clave": CLAVE})
        self.assertContains(r, "Demasiados intentos fallidos")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_cierre_de_sesion(self):
        """A3-Acceso | Login | Sesión iniciada | Cerrar sesión (POST) y volver a una ruta protegida | La sesión se cierra y la ruta exige login; GET de salir no está permitido"""
        self.entrar("funcionario")
        self.assertEqual(self.client.get("/cuenta/salir/").status_code, 405)
        r = self.client.post("/cuenta/salir/")
        self.assertRedirects(r, "/cuenta/ingresar/")
        r = self.client.get("/atenciones/")
        self.assertRedirects(r, "/cuenta/ingresar/?next=/atenciones/")

    def test_rutas_protegidas_sin_sesion(self):
        """A3-Acceso | Seguridad | Sin sesión | Acceder directamente a mantenedores, exportación y API | Todas redirigen al login"""
        for url in ["/", "/delegaciones/", "/roles/1/", "/usuarios/exportar/", "/atenciones/nueva/",
                    "/atenciones/api/vecinos/?q=an", "/modulo/vecinos/"]:
            r = self.client.get(url)
            self.assertEqual(r.status_code, 302, url)
            self.assertTrue(r["Location"].startswith("/cuenta/ingresar/"), url)


class RecuperacionTests(PruebaSGR):
    def solicitar(self, correo="funcionario@sgr.test"):
        return self.client.post("/cuenta/recuperar/", {"correo": correo})

    def codigo_enviado(self):
        cuerpo = mail.outbox[-1].body
        return cuerpo.split("Su código de verificación es: ")[1][:6]

    def test_respuesta_no_revela_existencia(self):
        """A3-Recuperación | Recuperar contraseña | Un correo registrado y otro inexistente | Solicitar código para ambos | Misma redirección y mensaje genérico; solo se envía correo a la cuenta existente"""
        r1 = self.solicitar("funcionario@sgr.test")
        self.client.session.flush()
        r2 = self.solicitar("nadie@sgr.test")
        self.assertEqual(r1["Location"], r2["Location"])
        self.assertMensaje(r1, "info", "Si el correo corresponde a una cuenta activa")
        self.assertMensaje(r2, "info", "Si el correo corresponde a una cuenta activa")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["funcionario@sgr.test"])

    def test_correo_invalido(self):
        """A3-Recuperación | Recuperar contraseña | Ninguna | Enviar un correo con formato inválido | Se rechaza indicando el formato correcto"""
        r = self.solicitar("no-es-correo")
        self.assertContains(r, "Ingrese un correo válido")

    def test_flujo_completo_y_nueva_clave(self):
        """A3-Recuperación | Recuperación completa | Usuario activo | Solicitar código, validarlo y guardar nueva clave | Ingreso con la nueva clave aceptado, la anterior rechazada y el código queda invalidado"""
        self.solicitar()
        codigo = self.codigo_enviado()
        r = self.client.post("/cuenta/recuperar/validar/", {"codigo": codigo})
        self.assertRedirects(r, "/cuenta/recuperar/nueva-clave/")
        r = self.client.post("/cuenta/recuperar/nueva-clave/", {"clave1": NUEVA, "clave2": NUEVA})
        self.assertRedirects(r, "/cuenta/ingresar/")
        self.assertMensaje(r, "success", "Contraseña actualizada")
        solicitud = SolicitudRecuperacion.objects.latest("creado")
        self.assertIsNotNone(solicitud.usado_en)
        r = self.client.post("/cuenta/ingresar/", {"identificador": "funcionario", "clave": CLAVE})
        self.assertContains(r, "incorrectos")
        r = self.client.post("/cuenta/ingresar/", {"identificador": "funcionario", "clave": NUEVA})
        self.assertRedirects(r, "/")

    def test_codigo_reutilizado(self):
        """A3-Recuperación | Validar código | Código ya usado para cambiar la clave | Volver a validar el mismo código | Se rechaza por código ya utilizado"""
        self.solicitar()
        codigo = self.codigo_enviado()
        self.client.post("/cuenta/recuperar/validar/", {"codigo": codigo})
        self.client.post("/cuenta/recuperar/nueva-clave/", {"clave1": NUEVA, "clave2": NUEVA})
        sesion = self.client.session
        sesion["recuperacion"] = {"token": SolicitudRecuperacion.objects.latest("creado").token,
                                  "correo": "funcionario@sgr.test", "verificado": False,
                                  "envio_simulado": timezone.now().isoformat()}
        sesion.save()
        r = self.client.post("/cuenta/recuperar/validar/", {"codigo": codigo})
        self.assertContains(r, "ya fue utilizado")

    def test_codigo_incorrecto_y_limite_intentos(self):
        """A3-Recuperación | Validar código | Código vigente; máximo 5 intentos | Ingresar 5 códigos erróneos y luego el correcto | Se descuentan intentos y luego se bloquea incluso el código correcto"""
        self.solicitar()
        codigo = self.codigo_enviado()
        malo = "000000" if codigo != "000000" else "111111"
        r = self.client.post("/cuenta/recuperar/validar/", {"codigo": malo})
        self.assertContains(r, "Le quedan 4 intento(s)")
        for _ in range(4):
            self.client.post("/cuenta/recuperar/validar/", {"codigo": malo})
        r = self.client.post("/cuenta/recuperar/validar/", {"codigo": codigo})
        self.assertContains(r, "Superó el máximo de intentos")
        self.assertEqual(self.client.get("/cuenta/recuperar/nueva-clave/").status_code, 302)

    def test_codigo_formato_invalido(self):
        """A3-Recuperación | Validar código | Solicitud vigente | Enviar letras o menos de 6 dígitos | Se rechaza por formato sin consumir intentos"""
        self.solicitar()
        r = self.client.post("/cuenta/recuperar/validar/", {"codigo": "12ab"})
        self.assertContains(r, "6 dígitos")
        self.assertEqual(SolicitudRecuperacion.objects.latest("creado").intentos, 0)

    def test_codigo_vencido(self):
        """A3-Recuperación | Validar código | Código con vigencia expirada (10 min referencial) | Validar el código correcto | Se rechaza por vencimiento"""
        self.solicitar()
        codigo = self.codigo_enviado()
        SolicitudRecuperacion.objects.update(expira=timezone.now() - timedelta(seconds=1))
        r = self.client.post("/cuenta/recuperar/validar/", {"codigo": codigo})
        self.assertContains(r, "El código venció")

    def test_reenvio_respeta_espera_e_invalida_anterior(self):
        """A3-Recuperación | Reenvío de código | Código recién enviado (espera 45 s referencial) | Reenviar de inmediato y luego tras la espera | Primero se rechaza; después se envía un código nuevo y el anterior deja de servir"""
        self.solicitar()
        anterior = self.codigo_enviado()
        r = self.client.post("/cuenta/recuperar/reenviar/")
        self.assertMensaje(r, "warning", "Espere")
        self.assertEqual(len(mail.outbox), 1)
        SolicitudRecuperacion.objects.update(ultimo_envio=timezone.now() - timedelta(seconds=46))
        r = self.client.post("/cuenta/recuperar/reenviar/")
        self.assertMensaje(r, "info", "nuevo código")
        self.assertEqual(len(mail.outbox), 2)
        nuevo = self.codigo_enviado()
        if nuevo != anterior:
            r = self.client.post("/cuenta/recuperar/validar/", {"codigo": anterior})
            self.assertContains(r, "Código incorrecto")
        r = self.client.post("/cuenta/recuperar/validar/", {"codigo": nuevo})
        self.assertRedirects(r, "/cuenta/recuperar/nueva-clave/")

    @override_settings(RECUPERACION_MAX_REENVIOS=1)
    def test_limite_de_reenvios(self):
        """A3-Recuperación | Reenvío de código | Máximo de reenvíos configurado en 1 | Reenviar dos veces respetando la espera | El segundo reenvío se rechaza"""
        self.solicitar()
        for _ in range(2):
            SolicitudRecuperacion.objects.update(ultimo_envio=timezone.now() - timedelta(seconds=60))
            r = self.client.post("/cuenta/recuperar/reenviar/")
        self.assertMensaje(r, "error", "máximo de reenvíos")
        self.assertEqual(len(mail.outbox), 2)

    @override_settings(RECUPERACION_MAX_SOLICITUDES_HORA=2)
    def test_limite_frecuencia_solicitudes(self):
        """A3-Recuperación | Recuperar contraseña | Límite de 2 solicitudes por hora | Solicitar 3 veces el código | La tercera mantiene la respuesta genérica pero no envía correo"""
        for _ in range(3):
            r = self.solicitar()
        self.assertMensaje(r, "info", "Si el correo corresponde")
        self.assertEqual(len(mail.outbox), 2)

    def test_nueva_clave_requiere_verificacion(self):
        """A3-Recuperación | Nueva contraseña | Código solicitado pero no validado | Abrir directamente la pantalla de nueva contraseña | Se bloquea y redirige a validar código"""
        self.assertRedirects(self.client.get("/cuenta/recuperar/nueva-clave/"), "/cuenta/recuperar/")
        self.solicitar()
        r = self.client.get("/cuenta/recuperar/nueva-clave/")
        self.assertRedirects(r, "/cuenta/recuperar/validar/")

    def test_nueva_clave_validaciones(self):
        """A3-Recuperación | Nueva contraseña | Código validado | Enviar clave débil, confirmación distinta y la clave anterior | Se rechazan los tres casos con su motivo"""
        self.solicitar()
        self.client.post("/cuenta/recuperar/validar/", {"codigo": self.codigo_enviado()})
        r = self.client.post("/cuenta/recuperar/nueva-clave/", {"clave1": "abc", "clave2": "abc"})
        self.assertContains(r, "La contraseña no cumple")
        r = self.client.post("/cuenta/recuperar/nueva-clave/", {"clave1": NUEVA, "clave2": NUEVA + "x"})
        self.assertContains(r, "Las contraseñas no coinciden")
        r = self.client.post("/cuenta/recuperar/nueva-clave/", {"clave1": CLAVE, "clave2": CLAVE})
        self.assertContains(r, "distinta de la anterior")
        self.assertTrue(Usuario.objects.get(username="funcionario").check_password(CLAVE))

    def test_flujo_simulado_para_correo_inexistente(self):
        """A3-Recuperación | Validar código | Correo no registrado | Validar cualquier código | Se informa código incorrecto (igual que una cuenta real) y nunca se habilita la nueva clave"""
        self.solicitar("nadie@sgr.test")
        r = self.client.post("/cuenta/recuperar/validar/", {"codigo": "123456"})
        self.assertContains(r, "Código incorrecto")
        self.assertEqual(self.client.get("/cuenta/recuperar/nueva-clave/").status_code, 302)
