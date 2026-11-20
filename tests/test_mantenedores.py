import re
from io import BytesIO
from unittest import mock

from django.core import mail
from django.db import DatabaseError
from openpyxl import load_workbook

from atenciones.models import Atencion, Vecino
from catalogos.models import Delegacion, Item, SubAtencion, TipoAtencion
from cuentas.models import Rol, Usuario
from matriz.models import MetaTrimestre

from .base import PruebaSGR


def leer_excel(respuesta):
    hoja = load_workbook(BytesIO(respuesta.content)).worksheets[0]
    return [[c.value for c in fila] for fila in hoja.iter_rows()]


class DelegacionesTests(PruebaSGR):
    def setUp(self):
        super().setUp()
        self.entrar("superadmin")

    def test_crear_consultar_editar(self):
        """A1-CRUD Delegaciones | Delegaciones | Superadministrador | Crear una delegación (sin ingresar código), consultarla y editar su nombre | El sistema asigna el código DEL-00008; registro visible en la ficha y actualizado con mensaje de éxito"""
        r = self.client.post("/delegaciones/nuevo/", {"codigo": "MANUAL", "nombre": "Delegación Prueba",
                                                       "direccion": "Calle 1", "comuna": "La Serena", "activo": "on"})
        d = Delegacion.objects.get(nombre="Delegación Prueba")
        self.assertEqual(d.codigo, "DEL-00008")
        self.assertRedirects(r, f"/delegaciones/{d.pk}/")
        self.assertMensaje(r, "success", "creada correctamente")
        self.assertContains(self.client.get(f"/delegaciones/{d.pk}/"), "Delegación Prueba")
        r = self.client.post(f"/delegaciones/{d.pk}/editar/", {"codigo": "OTRO", "nombre": "Delegación Editada",
                                                                "direccion": "Calle 2", "comuna": "La Serena",
                                                                "activo": "on"})
        self.assertMensaje(r, "success", "actualizada")
        d.refresh_from_db()
        self.assertEqual(d.nombre, "Delegación Editada")
        self.assertEqual(d.codigo, "DEL-00008")

    def test_requeridos_formato_longitud_duplicado(self):
        """A3-Validaciones | Delegaciones | Existe «Delegación Centro» | Enviar vacíos, nombre corto, dirección larga y nombre duplicado | Cada error se informa en su campo y no se crea registro"""
        total = Delegacion.objects.count()
        r = self.client.post("/delegaciones/nuevo/", {})
        self.assertContains(r, "Este campo es obligatorio", count=3)
        r = self.client.post("/delegaciones/nuevo/", {"nombre": "AB", "direccion": "x" * 151, "comuna": "La Serena"})
        self.assertContains(r, "al menos 3 caracteres")
        self.assertContains(r, "menos de 150 caracteres")
        r = self.client.post("/delegaciones/nuevo/", {"nombre": "delegación centro", "direccion": "x",
                                                       "comuna": "La Serena"})
        self.assertContains(r, "Ya existe una delegación con este nombre")
        self.assertSinExito(r)
        self.assertEqual(Delegacion.objects.count(), total)

    def test_eliminar_con_relaciones_y_sin_relaciones(self):
        """A1-CRUD Delegaciones | Delegaciones | DEL-00002 con usuarios; DEL-00005 sin relaciones | Eliminar ambas | DEL02 se rechaza sugiriendo desactivar; DEL-00005 se elimina"""
        r = self.client.post(f"/delegaciones/{self.del02.pk}/eliminar/")
        self.assertMensaje(r, "error", "Puede desactivarla")
        self.assertTrue(Delegacion.objects.filter(pk=self.del02.pk).exists())
        r = self.client.post(f"/delegaciones/{self.del05.pk}/eliminar/")
        self.assertMensaje(r, "success", "eliminada")
        self.assertFalse(Delegacion.objects.filter(pk=self.del05.pk).exists())

    def test_eliminar_requiere_post(self):
        """A3-Seguridad | Delegaciones | Superadministrador | Llamar eliminar por GET | Se responde 405 y no se elimina"""
        self.assertEqual(self.client.get(f"/delegaciones/{self.del04.pk}/eliminar/").status_code, 405)
        self.assertTrue(Delegacion.objects.filter(pk=self.del04.pk).exists())

    def test_desactivar_y_no_desactivar_activa(self):
        """A1-CRUD Delegaciones | Delegaciones | Contexto activo DEL-00001 | Desactivar DEL-00004 y luego DEL-00001 | DEL-00004 queda Inactiva; DEL-00001 se rechaza por ser la delegación activa"""
        r = self.client.post(f"/delegaciones/{self.del04.pk}/estado/")
        self.assertMensaje(r, "success", "inactiva")
        r = self.client.post(f"/delegaciones/{self.del01.pk}/estado/")
        self.assertMensaje(r, "error", "delegación activa")
        self.assertTrue(Delegacion.objects.get(pk=self.del01.pk).activo)


class RolesTests(PruebaSGR):
    def test_crear_rol_con_permisos(self):
        """A1-CRUD Roles | Roles | Superadministrador | Crear rol con permiso «items.editar» | Se crea con código automático ROL-00005 e incluye items.ver e inicio.ver"""
        self.entrar("superadmin")
        r = self.client.post("/roles/nuevo/", {"nombre": "Auditor", "descripcion": "x",
                                               "alcance": "DELEGACION", "activo": "on", "permisos": ["items.editar"]})
        rol = Rol.objects.get(nombre="Auditor")
        self.assertEqual(rol.codigo, "ROL-00005")
        self.assertRedirects(r, f"/roles/{rol.pk}/")
        self.assertEqual(set(rol.permisos), {"inicio.ver", "items.ver", "items.editar"})

    def test_rol_sin_permisos_y_duplicado(self):
        """A3-Validaciones | Roles | Existe rol «Coordinador» | Crear rol sin permisos y con nombre duplicado en minúsculas | Se rechaza ambos errores"""
        self.entrar("superadmin")
        r = self.client.post("/roles/nuevo/", {"nombre": "coordinador", "alcance": "DELEGACION"})
        self.assertContains(r, "Seleccione al menos un permiso")
        self.assertContains(r, "Ya existe un rol con este nombre")

    def test_rol_sistema_protegido(self):
        """A1-CRUD Roles | Roles | Rol Superadministrador (sistema) | Eliminar y desactivar el rol | Ambas operaciones se rechazan"""
        self.entrar("superadmin")
        rol = Rol.objects.get(es_sistema=True)
        self.assertMensaje(self.client.post(f"/roles/{rol.pk}/eliminar/"), "error", "protegido")
        self.assertMensaje(self.client.post(f"/roles/{rol.pk}/estado/"), "error", "protegido")
        self.assertTrue(Rol.objects.filter(pk=rol.pk, activo=True).exists())

    def test_rol_con_usuarios_no_se_elimina(self):
        """A1-CRUD Roles | Roles | Rol Funcionario con usuarios | Eliminar el rol | Se rechaza por usuarios asignados"""
        self.entrar("superadmin")
        rol = Rol.objects.get(nombre="Funcionario")
        r = self.client.post(f"/roles/{rol.pk}/eliminar/")
        self.assertMensaje(r, "error", "usuario(s) asignado(s)")

    def test_coordinador_solo_consulta_roles(self):
        """A2-Perfil | Roles | Coordinador con permiso roles.ver | Consultar roles y luego intentar crear o editar por URL | Puede listar; crear/editar responde 403"""
        self.entrar("coordinador")
        self.assertEqual(self.client.get("/roles/").status_code, 200)
        self.assertEqual(self.client.get("/roles/nuevo/").status_code, 403)
        self.assertEqual(self.client.post("/roles/1/editar/", {}).status_code, 403)


class UsuariosTests(PruebaSGR):
    def datos(self, **extra):
        rol = Rol.objects.get(nombre="Funcionario")
        base = {"nombre": "Usuario Nuevo", "username": "Nuevo.User", "correo": "Nuevo@SGR.test", "rol": rol.pk,
                "cargo": "GESTOR_SOCIAL", "delegaciones": [self.del01.pk], "is_active": "on"}
        base.update(extra)
        return base

    def test_crear_editar_usuario(self):
        """A1-CRUD Usuarios | Usuarios | Superadministrador | Crear usuario Funcionario en DEL-00001 (sin ingresar contraseña) y editar su nombre | Se crea normalizado, con clave provisoria enviada por correo y marcada para cambio; la edición conserva la clave"""
        self.entrar("superadmin")
        r = self.client.post("/usuarios/nuevo/", self.datos())
        u = Usuario.objects.get(username="nuevo.user")
        self.assertRedirects(r, f"/usuarios/{u.pk}/")
        self.assertEqual(u.correo, "nuevo@sgr.test")
        self.assertEqual(u.cargo, "GESTOR_SOCIAL")
        self.assertTrue(u.debe_cambiar_clave)
        self.assertEqual(mail.outbox[-1].to, ["nuevo@sgr.test"])
        clave = re.search(r"Clave provisoria: (\S+)", mail.outbox[-1].body).group(1)
        self.assertTrue(u.check_password(clave))
        self.assertMensaje(r, "info", "clave provisoria")
        self.client.post(f"/usuarios/{u.pk}/editar/", self.datos(nombre="Usuario Editado"))
        u.refresh_from_db()
        self.assertEqual(u.nombre, "Usuario Editado")
        self.assertTrue(u.check_password(clave))

    def test_validaciones_usuario(self):
        """A3-Validaciones | Usuarios | Existe funcionario@sgr.test | Crear con correo duplicado y dos delegaciones para un rol de una delegación | Cada regla se informa, no se crea el usuario ni se envía correo"""
        self.entrar("superadmin")
        r = self.client.post("/usuarios/nuevo/", self.datos(correo="FUNCIONARIO@sgr.test",
                                                             delegaciones=[self.del01.pk, self.del02.pk]))
        self.assertContains(r, "Ya existe un usuario con este correo")
        self.assertContains(r, "marque exactamente una")
        self.assertFalse(Usuario.objects.filter(username="nuevo.user").exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_no_eliminar_ni_desactivar_propia_cuenta(self):
        """A1-CRUD Usuarios | Usuarios | Superadministrador en sesión | Eliminar y desactivar su propia cuenta | Ambas se rechazan"""
        yo = self.entrar("superadmin")
        self.assertMensaje(self.client.post(f"/usuarios/{yo.pk}/eliminar/"), "error", "propia cuenta")
        self.assertMensaje(self.client.post(f"/usuarios/{yo.pk}/estado/"), "error", "propia cuenta")

    def test_usuario_con_atenciones_solo_se_desactiva(self):
        """A1-CRUD Usuarios | Usuarios | Funcionario responsable de una atención | Eliminarlo y luego desactivarlo | Eliminar se rechaza; desactivar se acepta"""
        self.entrar("superadmin")
        f = Usuario.objects.get(username="funcionario")
        Atencion.objects.create(vecino=Vecino.objects.first(), tipo=TipoAtencion.objects.first(),
                                subatencion=SubAtencion.objects.first(), descripcion="Prueba de relación",
                                delegacion=self.del01, responsable=f)
        self.assertMensaje(self.client.post(f"/usuarios/{f.pk}/eliminar/"), "error", "responsable de 1")
        self.assertMensaje(self.client.post(f"/usuarios/{f.pk}/estado/"), "success", "inactivo")

    def test_coordinador_no_escala_privilegios(self):
        """A2-Perfil | Usuarios | Coordinador (DEL-00001 a DEL-00003) | Crear usuario con rol Superadministrador y con delegación DEL-00004 no autorizada | Ambas opciones se rechazan por el servidor"""
        self.entrar("coordinador")
        superadmin = Rol.objects.get(es_sistema=True)
        r = self.client.post("/usuarios/nuevo/", self.datos(rol=superadmin.pk))
        self.assertContains(r, "Escoja una opción válida")
        r = self.client.post("/usuarios/nuevo/", self.datos(delegaciones=[self.del04.pk]))
        self.assertContains(r, "Escoja una opción válida")
        self.assertFalse(Usuario.objects.filter(username="nuevo.user").exists())

    def test_coordinador_conserva_delegaciones_fuera_de_alcance(self):
        """A2-Perfil | Usuarios | Delegado con DEL-00001; coordinador edita | Editar el usuario dejando sus delegaciones | Se conserva la asignación sin exponer delegaciones ajenas"""
        u = Usuario.objects.get(username="delegado")
        self.entrar("coordinador")
        r = self.client.post(f"/usuarios/{u.pk}/editar/", {
            "nombre": "Daniela Delegada", "username": "delegado", "correo": "delegado@sgr.test",
            "rol": u.rol_id, "delegaciones": [self.del01.pk], "is_active": "on"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(list(u.delegaciones.values_list("codigo", flat=True)), ["DEL-00001"])

    def test_listado_alcance_por_delegacion(self):
        """A2-Delegación | Usuarios | Coordinador con DEL-00001 activa | Listar usuarios, cambiar a DEL-00002 y volver a listar | Solo ve usuarios de la delegación activa y nunca al Superadministrador"""
        self.entrar("coordinador")
        r = self.client.get("/usuarios/")
        self.assertContains(r, "Fernanda Funcionaria")
        self.assertNotContains(r, "Felipe Funcionario")
        self.assertNotContains(r, "Sofía Superadmin")
        self.client.post("/contexto/delegacion/", {"delegacion": self.del02.pk, "siguiente": "/usuarios/"})
        r = self.client.get("/usuarios/")
        self.assertContains(r, "Felipe Funcionario")
        self.assertNotContains(r, "Fernanda Funcionaria")

    def test_exportacion_sin_campos_sensibles(self):
        """A2-Exportar | Usuarios | Superadministrador, ámbito todas | Exportar a Excel | El archivo trae todos los usuarios filtrados y no incluye contraseñas ni tokens"""
        self.entrar("superadmin")
        r = self.client.get("/usuarios/exportar/?ambito=todas")
        self.assertEqual(r["Content-Type"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        filas = leer_excel(r)
        self.assertEqual(len(filas) - 1, Usuario.objects.count())
        texto = str(filas).lower()
        self.assertNotIn("pbkdf2", texto)
        self.assertNotIn("md5$", texto)
        self.assertFalse(any("contrase" in str(c).lower() or "token" in str(c).lower() for c in filas[0]))


class ItemsTests(PruebaSGR):
    def setUp(self):
        super().setUp()
        # 25 ítems adicionales («Meta de gestión NN», 3 inactivos) para probar búsqueda y paginación.
        for i in range(1, 26):
            Item.objects.create(nombre=f"Meta de gestión {i:02d}", activo=i % 7 != 0,
                                descripcion=f"Ítem de ejemplo N° {i} para el seguimiento de metas del proyecto.")
        self.entrar("coordinador")

    def test_crud_item(self):
        """A1-CRUD Ítems y metas | Ítems de la matriz | Coordinador | Crear (sin código manual), consultar, editar, desactivar y eliminar un ítem | Código ITM-00000 automático; cada operación se completa con su mensaje de éxito"""
        r = self.client.post("/items/nuevo/", {"codigo": "IT90", "nombre": "Meta nueva", "descripcion": "Desc",
                                               "ambito": "GES", "activo": "on"})
        i = Item.objects.get(nombre="Meta nueva")
        self.assertRegex(i.codigo, r"^ITM-\d{5}$")
        self.assertMensaje(r, "success", "creado")
        self.assertContains(self.client.get(f"/items/{i.pk}/"), "Meta nueva")
        self.client.post(f"/items/{i.pk}/editar/", {"nombre": "Meta editada", "ambito": "GES", "activo": "on"})
        self.assertEqual(Item.objects.get(pk=i.pk).nombre, "Meta editada")
        self.client.post(f"/items/{i.pk}/estado/")
        self.assertFalse(Item.objects.get(pk=i.pk).activo)
        r = self.client.post(f"/items/{i.pk}/eliminar/")
        self.assertMensaje(r, "success", "eliminado")
        self.assertFalse(Item.objects.filter(pk=i.pk).exists())

    def test_busqueda_paginacion_y_filtros(self):
        """A2-Listados | Ítems de la matriz | 25 ítems «Meta de gestión» (22 activos) | Buscar «META» (mayúsculas), filtrar Activo y pasar a la página 2 | Coincidencia parcial sin distinguir mayúsculas, total correcto y filtros conservados en el paginador"""
        r = self.client.get("/items/?q=META&estado=activo")
        self.assertEqual(r.context["total"], Item.objects.filter(activo=True, nombre__icontains="meta").count())
        self.assertContains(r, "q=META&amp;estado=activo&amp;pagina=2")
        r = self.client.get("/items/?q=META&estado=activo&pagina=2")
        self.assertEqual(r.context["pagina"].number, 2)
        self.assertEqual(r.context["q"], "META")
        r = self.client.get("/items/?q=n%C2%B0%2012")
        self.assertEqual(r.context["total"], 1)

    def test_estados_vacio_y_sin_coincidencias(self):
        """A2-Listados | Ítems y metas | Catálogo con datos y luego vacío | Buscar un texto inexistente y luego listar sin registros | Se muestra «Sin coincidencias» y luego «No hay registros»"""
        self.assertContains(self.client.get("/items/?q=zzzz"), "Sin coincidencias")
        MetaTrimestre.objects.all().delete()
        Item.objects.all().delete()
        self.assertContains(self.client.get("/items/"), "No hay registros")

    def test_exportacion_coherente_con_tabla(self):
        """A2-Exportar | Ítems y metas | Filtro q=meta y estado=inactivo | Comparar la tabla con el Excel exportado | Mismos registros en el mismo orden, en todas las páginas"""
        r = self.client.get("/items/?q=meta&estado=inactivo")
        codigos_tabla = [f["obj"].codigo for f in r.context["filas"]]
        filas = leer_excel(self.client.get("/items/exportar/?q=meta&estado=inactivo"))
        self.assertEqual([f[0] for f in filas[1:]], codigos_tabla)
        filas = leer_excel(self.client.get("/items/exportar/"))
        self.assertEqual(len(filas) - 1, Item.objects.count())

    def test_parametros_invalidos_no_rompen_listado(self):
        """A2-Listados | Ítems y metas | Ninguna | Enviar página inexistente y filtro de estado inválido | El listado responde 200 sin aplicar el filtro inválido"""
        r = self.client.get("/items/?pagina=999&estado=hackeo")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["total"], Item.objects.count())

    def test_error_de_servidor_no_muestra_exito(self):
        """A3-SweetAlert2 | Ítems y metas | Falla simulada de base de datos al guardar | Crear un ítem válido | Se muestra error, no éxito, y no se crea el registro"""
        with mock.patch("catalogos.views.ItemForm.save", side_effect=DatabaseError("caída")):
            r = self.client.post("/items/nuevo/", {"nombre": "Meta error", "ambito": "GES", "activo": "on"})
        self.assertMensaje(r, "error", "error del servidor")
        self.assertSinExito(r)
        self.assertFalse(Item.objects.filter(nombre="Meta error").exists())


class TipoSubAtencionTests(PruebaSGR):
    def setUp(self):
        super().setUp()
        self.entrar("coordinador")
        self.tipo = TipoAtencion.objects.get(nombre="Social")

    def test_crud_tipo(self):
        """A1-CRUD Tipo de Atención | Tipo de Atención | Coordinador | Crear, editar y eliminar un tipo sin relaciones | Operaciones completadas"""
        self.client.post("/tipos-atencion/nuevo/", {"nombre": "Deportes", "activo": "on"})
        t = TipoAtencion.objects.get(nombre="Deportes")
        self.assertEqual(t.codigo, "TAT-00007")
        self.client.post(f"/tipos-atencion/{t.pk}/editar/", {"nombre": "Deportes y recreación",
                                                             "activo": "on"})
        self.assertEqual(TipoAtencion.objects.get(pk=t.pk).nombre, "Deportes y recreación")
        r = self.client.post(f"/tipos-atencion/{t.pk}/eliminar/")
        self.assertMensaje(r, "success", "eliminado")

    def test_tipo_con_subatenciones_relacionadas(self):
        """A3-Tipo y Sub Atención | Tipo de Atención | TAT-00001 con sub atenciones activas | Eliminar TAT-00001 y desactivarlo | Ambas operaciones se rechazan por integridad"""
        self.assertMensaje(self.client.post(f"/tipos-atencion/{self.tipo.pk}/eliminar/"), "error", "sub atención")
        self.assertMensaje(self.client.post(f"/tipos-atencion/{self.tipo.pk}/estado/"), "error", "Desactívelas primero")
        self.assertTrue(TipoAtencion.objects.get(pk=self.tipo.pk).activo)

    def test_crud_subatencion(self):
        """A1-CRUD Sub Atención | Sub Atención | Coordinador | Crear sub atención asociada a TAT-00001, editarla y eliminarla | Se guarda con su tipo asociado y se elimina sin relaciones"""
        self.client.post("/sub-atenciones/nuevo/", {"nombre": "Becas", "tipo": self.tipo.pk,
                                                    "activo": "on"})
        s = SubAtencion.objects.get(nombre="Becas")
        self.assertEqual(s.tipo, self.tipo)
        self.assertContains(self.client.get("/sub-atenciones/?q=becas"), "Social")
        r = self.client.post(f"/sub-atenciones/{s.pk}/eliminar/")
        self.assertMensaje(r, "success", "eliminada")

    def test_subatencion_validaciones(self):
        """A3-Tipo y Sub Atención | Sub Atención | TAT-00006 inactivo; «Ayuda social» existe en TAT-00001 | Crear con tipo inactivo y con nombre duplicado dentro del tipo | Se rechazan ambos"""
        inactivo = TipoAtencion.objects.get(nombre="Cultura (inactivo)")
        r = self.client.post("/sub-atenciones/nuevo/", {"nombre": "X1", "tipo": inactivo.pk,
                                                        "activo": "on"})
        self.assertContains(r, "Escoja una opción válida")
        r = self.client.post("/sub-atenciones/nuevo/", {"nombre": "AYUDA SOCIAL",
                                                        "tipo": self.tipo.pk, "activo": "on"})
        self.assertContains(r, "Ya existe una sub atención con este nombre")

    def test_subatencion_con_atenciones_y_cambio_de_tipo(self):
        """A3-Tipo y Sub Atención | Sub Atención | Sub atención usada en una atención | Eliminarla y cambiar su tipo | Se rechaza eliminar y cambiar de tipo"""
        s = SubAtencion.objects.get(nombre="Ayuda social")
        Atencion.objects.create(vecino=Vecino.objects.first(), tipo=s.tipo, subatencion=s, descripcion="Relación",
                                delegacion=self.del01, responsable=Usuario.objects.get(username="funcionario"))
        self.assertMensaje(self.client.post(f"/sub-atenciones/{s.pk}/eliminar/"), "error", "atención(es)")
        otro = TipoAtencion.objects.get(nombre="Infraestructura")
        r = self.client.post(f"/sub-atenciones/{s.pk}/editar/", {"nombre": s.nombre,
                                                                 "tipo": otro.pk, "activo": "on"})
        self.assertContains(r, "No se puede cambiar el tipo")

    def test_filtro_por_tipo(self):
        """A2-Listados | Sub Atención | 3 sub atenciones en TAT-00001 | Filtrar por tipo TAT-00001 y estado activa | Solo aparecen las 3 de TAT-00001"""
        r = self.client.get(f"/sub-atenciones/?tipo={self.tipo.pk}&estado=activo")
        self.assertEqual(r.context["total"], 3)
