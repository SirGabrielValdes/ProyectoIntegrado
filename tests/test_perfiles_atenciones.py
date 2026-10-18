from atenciones.models import Atencion, Vecino
from catalogos.models import SubAtencion, TipoAtencion
from cuentas.models import Usuario

from .base import PruebaSGR


class PerfilesTests(PruebaSGR):
    def test_menu_funcionario(self):
        """A10-Roles | Menú | Funcionario | Ingresar y revisar el menú | Solo ve Inicio, Atenciones y Vecinos (plantilla); no ve mantenedores"""
        self.entrar("funcionario")
        r = self.client.get("/")
        menu = [i["modulo"] for i in r.context["menu"]]
        self.assertEqual(menu, ["inicio", "atenciones", "vecinos"])

    def test_menu_por_rol(self):
        """A10-Roles | Menú | Los 4 roles definidos | Ingresar con cada rol | Cada uno ve únicamente sus módulos autorizados"""
        esperado = {
            "superadmin": {"delegaciones", "roles", "usuarios", "items", "tipos", "subatenciones", "atenciones",
                           "auditoria"},
            "coordinador": {"delegaciones", "roles", "usuarios", "items", "tipos", "subatenciones", "atenciones"},
            "delegado": {"delegaciones", "usuarios", "items", "tipos", "subatenciones", "atenciones", "reportes"},
            "funcionario": {"atenciones", "vecinos"},
        }
        prohibido = {"coordinador": {"auditoria"}, "delegado": {"roles", "auditoria"},
                     "funcionario": {"delegaciones", "roles", "usuarios", "items", "tipos", "subatenciones"}}
        for usuario, modulos in esperado.items():
            self.client.logout()
            self.entrar(usuario)
            menu = {i["modulo"] for i in self.client.get("/").context["menu"]}
            self.assertTrue(modulos <= menu, f"{usuario}: faltan {modulos - menu}")
            self.assertFalse(prohibido.get(usuario, set()) & menu, f"{usuario}: ve módulos no autorizados")

    def test_acceso_directo_por_url_rechazado(self):
        """A2-Perfil | Seguridad | Funcionario sin permisos de mantenedores | Abrir por URL listados, creación, exportación y módulo de auditoría | El servidor responde 403 en todos los casos"""
        self.entrar("funcionario")
        for url in ["/delegaciones/", "/roles/", "/usuarios/", "/usuarios/nuevo/", "/items/exportar/",
                    "/tipos-atencion/", "/sub-atenciones/1/editar/", "/modulo/auditoria/"]:
            self.assertEqual(self.client.get(url).status_code, 403, url)
        self.assertEqual(self.client.post("/items/1/eliminar/").status_code, 403)

    def test_delegado_solo_lectura(self):
        """A2-Perfil | Ítems y metas | Delegado municipal con permiso de ver | Listar ítems y luego editar uno por URL | Puede ver; editar responde 403 y no se muestran botones de edición"""
        self.entrar("delegado")
        r = self.client.get("/items/")
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, "/items/1/editar/")
        self.assertEqual(self.client.get("/items/1/editar/").status_code, 403)

    def test_distintivo_delegacion_fija(self):
        """A2-Delegación | Cabecera | Funcionario con una sola delegación | Abrir cualquier pantalla | La cabecera muestra código, nombre, usuario, rol e indica contexto fijo sin selector"""
        self.entrar("funcionario")
        r = self.client.get("/atenciones/")
        self.assertContains(r, 'data-delegacion-activa="DEL01"')
        self.assertContains(r, "Delegación Centro")
        self.assertContains(r, "Fernanda Funcionaria")
        self.assertContains(r, "Funcionario")
        self.assertContains(r, "Fija")
        self.assertNotContains(r, 'id="selector-delegacion"')

    def test_selector_solo_delegaciones_autorizadas(self):
        """A2-Delegación | Cabecera | Coordinador con DEL01, DEL02 y DEL03 | Revisar el selector de delegación | Solo lista las 3 autorizadas"""
        self.entrar("coordinador")
        r = self.client.get("/")
        codigos = [d.codigo for d in r.context["delegaciones_autorizadas"]]
        self.assertEqual(codigos, ["DEL01", "DEL02", "DEL03"])
        self.assertNotContains(r, "DEL04 |")

    def test_cambio_a_delegacion_no_autorizada(self):
        """A2-Delegación | Contexto | Coordinador sin DEL04; funcionario con solo DEL01 | Enviar POST de cambio de contexto a DEL04 / DEL02 alterando la solicitud | El servidor responde 403 y el contexto no cambia"""
        self.entrar("coordinador")
        r = self.client.post("/contexto/delegacion/", {"delegacion": self.del04.pk})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.client.session["delegacion_activa_id"], self.del01.pk)
        self.client.logout()
        self.entrar("funcionario")
        self.assertEqual(self.client.post("/contexto/delegacion/", {"delegacion": self.del02.pk}).status_code, 403)

    def test_sesion_manipulada_se_corrige(self):
        """A2-Delegación | Contexto | Funcionario de DEL01 | Forzar en la sesión una delegación ajena (DEL02) | El servidor la reemplaza por una autorizada"""
        self.entrar("funcionario")
        s = self.client.session
        s["delegacion_activa_id"] = self.del02.pk
        s.save()
        r = self.client.get("/")
        self.assertEqual(r.context["delegacion_activa"], self.del01)

    def test_cambio_contexto_actualiza_listado(self):
        """A2-Delegación | Contexto | Coordinador; atenciones en DEL01 y DEL02 | Cambiar de DEL01 a DEL02 desde un formulario | Redirige al listado del módulo y solo muestra atenciones de DEL02"""
        self.entrar("coordinador")
        crear_atencion(self.del01, "funcionario")
        crear_atencion(self.del02, "funcionario2")
        self.assertEqual(self.client.get("/atenciones/").context["total"], 1)
        r = self.client.post("/contexto/delegacion/", {"delegacion": self.del02.pk, "siguiente": "/atenciones/nueva/"})
        self.assertRedirects(r, "/atenciones/")
        r = self.client.get("/atenciones/")
        self.assertEqual([f["obj"].delegacion.codigo for f in r.context["filas"]], ["DEL02"])


def crear_atencion(delegacion, username):
    s = SubAtencion.objects.get(codigo="SA01")
    return Atencion.objects.create(vecino=Vecino.objects.first(), tipo=s.tipo, subatencion=s,
                                   descripcion="Atención de prueba", delegacion=delegacion,
                                   responsable=Usuario.objects.get(username=username))


class IngresoAtencionTests(PruebaSGR):
    def setUp(self):
        super().setUp()
        self.usuario = self.entrar("funcionario")
        self.tipo = TipoAtencion.objects.get(codigo="TA01")
        self.sub = SubAtencion.objects.get(codigo="SA01")
        self.vecino = Vecino.objects.first()

    def token(self):
        r = self.client.get("/atenciones/nueva/")
        return r.context["form"]["token"].value()

    def datos(self, **extra):
        base = {"modo_vecino": "existente", "vecino": self.vecino.pk, "tipo": self.tipo.pk,
                "subatencion": self.sub.pk, "descripcion": "Solicita orientación sobre ayudas sociales.",
                "token": self.token()}
        base.update(extra)
        return base

    def test_registro_con_contexto_del_servidor(self):
        """A2-Ingreso de atención | Atenciones | Funcionario en DEL01 | Guardar una atención enviando además una delegación y responsable ajenos en la solicitud | Se registra con DEL01, el usuario de sesión y la fecha automática; se muestra el folio"""
        datos = self.datos(delegacion=self.del02.pk, responsable=1)
        r = self.client.post("/atenciones/nueva/", datos)
        a = Atencion.objects.get()
        self.assertRedirects(r, f"/atenciones/{a.pk}/")
        self.assertEqual(a.delegacion, self.del01)
        self.assertEqual(a.responsable, self.usuario)
        self.assertIsNotNone(a.fecha_registro)
        self.assertMensaje(r, "success", a.folio)
        self.assertTrue(a.folio.startswith("AT-"))

    def test_campos_obligatorios(self):
        """A3-Ingreso de atención | Atenciones | Funcionario | Guardar sin solicitante, tipo, sub atención ni descripción | Se informan todos los obligatorios y no se crea registro"""
        r = self.client.post("/atenciones/nueva/", {"modo_vecino": "existente", "token": self.token()})
        for texto in ["Busque y seleccione al vecino", "Seleccione el Tipo de Atención", "Describa la solicitud"]:
            self.assertContains(r, texto)
        self.assertSinExito(r)
        self.assertEqual(Atencion.objects.count(), 0)

    def test_dependencia_tipo_subatencion(self):
        """A3-Tipo y Sub Atención | Atenciones | SA04 pertenece a TA02 | Enviar TA01 con la sub atención SA04 | Se rechaza por no corresponder al tipo"""
        otra = SubAtencion.objects.get(codigo="SA04")
        r = self.client.post("/atenciones/nueva/", self.datos(subatencion=otra.pk))
        self.assertContains(r, "La Sub Atención no es válida")
        self.assertEqual(Atencion.objects.count(), 0)

    def test_api_subatenciones_solo_activas_del_tipo(self):
        """A2-Ingreso de atención | Atenciones | TA01 con 3 sub atenciones; se desactiva SA02 | Consultar las sub atenciones de TA01 | Solo se devuelven las activas del tipo (2)"""
        SubAtencion.objects.filter(codigo="SA02").update(activo=False)
        datos = self.client.get(f"/atenciones/api/subatenciones/?tipo={self.tipo.pk}").json()
        self.assertEqual({r["texto"] for r in datos["resultados"]}, {"Ayuda social", "Registro Social de Hogares"})

    def test_subatencion_inactiva_rechazada(self):
        """A3-Ingreso de atención | Atenciones | SA01 desactivada | Guardar una atención con SA01 | Se rechaza por sub atención inactiva"""
        SubAtencion.objects.filter(pk=self.sub.pk).update(activo=False)
        r = self.client.post("/atenciones/nueva/", self.datos())
        self.assertContains(r, "La Sub Atención no es válida o está inactiva")

    def test_nuevo_vecino_con_rut(self):
        """A2-Ingreso de atención | Atenciones | Vecino no registrado | Registrar nuevo vecino con RUT inválido y luego válido | El RUT inválido se rechaza; con RUT válido se crean vecino y atención"""
        r = self.client.post("/atenciones/nueva/", self.datos(modo_vecino="nuevo", vecino="", rut="12.345.678-0",
                                                             nombre="Vecino Nuevo"))
        self.assertContains(r, "dígito verificador")
        r = self.client.post("/atenciones/nueva/", self.datos(modo_vecino="nuevo", vecino="", rut="12.345.678-5",
                                                             nombre="Vecino Nuevo"))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Atencion.objects.get().vecino.rut, "123456785")

    def test_prevencion_doble_envio(self):
        """A3-Ingreso de atención | Atenciones | Formulario con token único | Enviar dos veces el mismo formulario | Solo se crea una atención; el segundo envío informa el folio existente"""
        datos = self.datos()
        self.client.post("/atenciones/nueva/", datos)
        r = self.client.post("/atenciones/nueva/", datos)
        self.assertEqual(Atencion.objects.count(), 1)
        self.assertMensaje(r, "warning", "ya fue registrada")

    def test_cancelar_no_crea_registro(self):
        """A2-Ingreso de atención | Atenciones | Formulario abierto | Pulsar Cancelar (vuelve al listado) | No se crea ninguna atención"""
        self.client.get("/atenciones/nueva/")
        r = self.client.get("/atenciones/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Atencion.objects.count(), 0)

    def test_no_ver_atencion_de_otra_delegacion(self):
        """A2-Delegación | Atenciones | Atención registrada en DEL02 | Funcionario de DEL01 abre su URL directamente | Responde 404 (fuera de alcance)"""
        a = crear_atencion(self.del02, "funcionario2")
        self.assertEqual(self.client.get(f"/atenciones/{a.pk}/").status_code, 404)

    def test_busqueda_vecino(self):
        """A2-Ingreso de atención | Atenciones | Vecinos cargados | Buscar vecino por parte del RUT y del nombre | Se devuelven coincidencias"""
        v = self.vecino
        self.assertTrue(self.client.get(f"/atenciones/api/vecinos/?q={v.rut[:5]}").json()["resultados"])
        self.assertTrue(self.client.get(f"/atenciones/api/vecinos/?q={v.nombre.split()[0].lower()}").json()["resultados"])
