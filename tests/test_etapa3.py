"""Pruebas de la Etapa 3: correcciones, matriz SGR, semáforo, tubo de trabajo y API móvil."""
import importlib
import json
import re
from datetime import date
from io import BytesIO
from unittest import mock

from django.apps import apps as registro
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from catalogos.models import Delegacion, Item, SubAtencion, TipoAtencion
from cuentas.models import Rol, Usuario
from matriz import semaforo
from matriz.models import Actividad, Ausencia, MetaTrimestre, Organizacion, Trimestre
from tubo.models import Compromiso, Evidencia, TokenApi

from .base import CLAVE, PruebaSGR

MIERCOLES = date(2026, 11, 18)


def png(nombre="foto.png", formato="PNG"):
    salida = BytesIO()
    Image.new("RGB", (40, 30), (196, 18, 48)).save(salida, formato)
    return SimpleUploadedFile(nombre, salida.getvalue(), content_type=f"image/{formato.lower()}")


def pdf():
    return SimpleUploadedFile("respaldo.pdf", b"%PDF-1.4 respaldo de prueba", content_type="application/pdf")


def hoy_es(fecha):
    return mock.patch("django.utils.timezone.localdate", return_value=fecha)


class MatrizBase(PruebaSGR):
    """Trimestre abierto del 1-oct al 31-dic de 2026 con metas para Gestor Social."""

    def setUp(self):
        super().setUp()
        Trimestre.objects.update(estado="CERRADO")
        self.trimestre = Trimestre.objects.create(nombre="Trimestre de prueba", inicio=date(2026, 10, 1),
                                                  fin=date(2026, 12, 31), estado="ABIERTO")
        self.item = Item.objects.get(nombre="Visitas en terreno")
        self.item_ges = Item.objects.get(nombre="Talleres y actividades con organizaciones")
        self.felicitacion = Item.objects.get(es_felicitacion=True)
        MetaTrimestre.objects.create(trimestre=self.trimestre, item=self.item, cargo="GESTOR_SOCIAL", cantidad=10)
        self.funcionaria = Usuario.objects.get(username="funcionario")

    def actividad(self, **extra):
        datos = {"item": self.item.pk, "fecha": "2026-11-18", "tipo_registro": "EJECUTADA",
                 "solicitante_tipo": "VECINO", "nombre_contacto": "Marta Henríquez",
                 "telefono_contacto": "+56 9 1111 2222", "descripcion": "Visita domiciliaria por solicitud de ayuda."}
        datos.update(extra)
        return datos

    def registrar(self, hoy=MIERCOLES, **extra):
        with hoy_es(hoy):
            return self.client.post("/actividades/nuevo/", self.actividad(**extra))


# =============================================================================
# Correcciones de la entrega anterior
# =============================================================================
class CorreccionesTests(PruebaSGR):
    def test_codigos_automaticos_y_no_editables(self):
        """E3-Código automático | Mantenedores | Superadministrador | Crear delegación, ítem, tipo, sub atención y rol enviando un código manual, y editar enviando otro | El sistema asigna PREFIJO-00000 correlativo e ignora los códigos enviados"""
        self.entrar("superadmin")
        self.client.post("/delegaciones/nuevo/", {"codigo": "XX1", "nombre": "Delegación Norte Alto",
                                                   "direccion": "Calle 2", "comuna": "La Serena", "activo": "on"})
        d = Delegacion.objects.get(nombre="Delegación Norte Alto")
        self.assertEqual(d.codigo, "DEL-00008")
        self.client.post("/items/nuevo/", {"codigo": "ZZ", "nombre": "Ítem nuevo", "ambito": "SOC", "activo": "on"})
        self.assertRegex(Item.objects.get(nombre="Ítem nuevo").codigo, r"^ITM-\d{5}$")
        self.client.post("/tipos-atencion/nuevo/", {"nombre": "Deportes", "activo": "on"})
        tipo = TipoAtencion.objects.get(nombre="Deportes")
        self.client.post("/sub-atenciones/nuevo/", {"nombre": "Canchas", "tipo": tipo.pk, "activo": "on"})
        self.assertEqual(SubAtencion.objects.get(nombre="Canchas").codigo, "SAT-00013")
        self.client.post(f"/delegaciones/{d.pk}/editar/", {"codigo": "CAMBIO", "nombre": "Delegación Norte Alto",
                                                            "direccion": "Calle 3", "comuna": "La Serena", "activo": "on"})
        d.refresh_from_db()
        self.assertEqual(d.codigo, "DEL-00008")
        self.assertNotContains(self.client.get("/delegaciones/nuevo/"), 'name="codigo"')

    def test_renumeracion_de_codigos_antiguos(self):
        """E3-Código automático | Migración de datos | Registros con códigos antiguos (DEL01, ROL01, IT01) | Ejecutar la migración de renumeración | Quedan con el formato PREFIJO-00000 en orden de creación"""
        Delegacion.objects.filter(pk=self.del01.pk).update(codigo="DEL01")
        Rol.objects.filter(nombre="Superadministrador").update(codigo="ROL01")
        importlib.import_module("catalogos.migrations.0003_renumerar_codigos").renumerar(registro, None)
        importlib.import_module("cuentas.migrations.0003_renumerar_codigos_roles").renumerar(registro, None)
        self.assertEqual(Delegacion.objects.get(pk=self.del01.pk).codigo, "DEL-00001")
        self.assertTrue(all(re.fullmatch(r"ROL-\d{5}", c) for c in Rol.objects.values_list("codigo", flat=True)))

    def test_clave_provisoria_y_cambio_obligatorio(self):
        """E3-Clave provisoria | Usuarios | Superadministrador crea un usuario | Ingresar con la clave provisoria del correo, navegar y luego cambiarla | Llega el correo; toda ruta redirige al cambio de clave hasta definir una nueva; después ingresa normalmente"""
        self.entrar("superadmin")
        rol = Rol.objects.get(nombre="Funcionario")
        self.client.post("/usuarios/nuevo/", {"nombre": "Nuevo Funcionario", "username": "nuevo", "correo": "nuevo@sgr.test",
                                              "rol": rol.pk, "cargo": "GESTOR_SOCIAL", "delegaciones": [self.del01.pk],
                                              "is_active": "on"})
        provisoria = re.search(r"Clave provisoria: (\S+)", mail.outbox[-1].body).group(1)
        self.client.logout()
        r = self.client.post("/cuenta/ingresar/", {"identificador": "nuevo", "clave": provisoria})
        self.assertRedirects(r, "/", fetch_redirect_response=False)
        for url in ["/", "/atenciones/", "/actividades/nuevo/"]:
            self.assertRedirects(self.client.get(url), "/cuenta/cambiar-clave/")
        r = self.client.post("/cuenta/cambiar-clave/", {"clave1": provisoria, "clave2": provisoria})
        self.assertContains(r, "distinta de la anterior")
        r = self.client.post("/cuenta/cambiar-clave/", {"clave1": "Propia#2026x", "clave2": "Propia#2026x"})
        self.assertRedirects(r, "/")
        u = Usuario.objects.get(username="nuevo")
        self.assertFalse(u.debe_cambiar_clave)
        self.assertEqual(self.client.get("/atenciones/").status_code, 200)

    def test_reenviar_clave_provisoria(self):
        """E3-Clave provisoria | Usuarios | Usuario existente | Reenviar clave provisoria desde su ficha | Se envía una nueva clave, la anterior deja de funcionar y se exige cambio"""
        self.entrar("superadmin")
        f = Usuario.objects.get(username="funcionario")
        r = self.client.post(f"/usuarios/{f.pk}/reenviar-clave/")
        self.assertMensaje(r, "success", "nueva clave provisoria")
        f.refresh_from_db()
        self.assertTrue(f.debe_cambiar_clave)
        self.assertFalse(f.check_password(CLAVE))
        self.assertTrue(f.check_password(re.search(r"Clave provisoria: (\S+)", mail.outbox[-1].body).group(1)))
        self.assertEqual(self.client.get(f"/usuarios/{f.pk}/reenviar-clave/").status_code, 405)

    def test_busqueda_en_vivo_y_filas(self):
        """E3-Búsqueda en vivo | Listados | Coordinador; 25 ítems de prueba | Pedir la tabla con la cabecera de búsqueda en vivo y elegir 20 filas | Se devuelve solo la tabla filtrada; el tamaño de página se respeta y se conserva al paginar; valores no permitidos vuelven a 10"""
        for i in range(25):
            Item.objects.create(nombre=f"Meta adicional {i:02d}")
        self.entrar("coordinador")
        r = self.client.get("/items/?q=ADICIONAL&filas=20", HTTP_X_REQUESTED_WITH="fetch")
        self.assertNotContains(r, "<html")
        self.assertEqual(len(r.context["filas"]), 20)
        self.assertEqual(r.context["total"], 25)
        self.assertContains(r, "filas=20&amp;pagina=2")
        r = self.client.get("/items/?filas=7")
        self.assertEqual(r.context["filas_pagina"], 10)
        r = self.client.get("/items/")
        self.assertContains(r, 'name="filas"')
        for n in ("10", "20", "50", "100"):
            self.assertContains(r, f'<option value="{n}"')

    def test_comuna_por_defecto(self):
        """E3-Formularios | Delegaciones y organizaciones | Superadministrador | Abrir los formularios de creación | La comuna viene precargada con «La Serena» y sigue editable"""
        self.entrar("superadmin")
        for url in ("/delegaciones/nuevo/", "/organizaciones/nuevo/"):
            r = self.client.get(url)
            self.assertRegex(r.content.decode(), r'name="comuna"[^>]*value="La Serena"|value="La Serena"[^>]*name="comuna"')


# =============================================================================
# Trimestres, metas y organizaciones
# =============================================================================
class TrimestresTests(MatrizBase):
    def test_reglas_del_trimestre(self):
        """E3-Trimestres | Trimestres | Trimestre de prueba abierto | Crear uno con fechas invertidas, otro superpuesto y otro abierto | Se rechazan los tres; uno válido queda Planificado con código TRI-00000"""
        self.entrar("coordinador")
        r = self.client.post("/trimestres/nuevo/", {"nombre": "T inválido", "inicio": "2027-03-31", "fin": "2027-01-01",
                                                    "estado": "PLANIFICADO"})
        self.assertContains(r, "posterior a la de inicio")
        r = self.client.post("/trimestres/nuevo/", {"nombre": "T cruzado", "inicio": "2026-12-01", "fin": "2027-02-28",
                                                    "estado": "PLANIFICADO"})
        self.assertContains(r, "se superponen")
        r = self.client.post("/trimestres/nuevo/", {"nombre": "1.º trimestre 2027", "inicio": "2027-01-01",
                                                    "fin": "2027-03-31", "estado": "ABIERTO"})
        self.assertContains(r, "Ya hay un trimestre abierto")
        self.client.post("/trimestres/nuevo/", {"nombre": "1.º trimestre 2027", "inicio": "2027-01-01",
                                                "fin": "2027-03-31", "estado": "PLANIFICADO"})
        t = Trimestre.objects.get(nombre="1.º trimestre 2027")
        self.assertRegex(t.codigo, r"^TRI-\d{5}$")
        self.assertEqual(t.dias_habiles, 64)

    def test_configurar_metas(self):
        """E3-Metas | Trimestres | Coordinador | Guardar la grilla de metas con valores válidos e inválidos | Los inválidos se rechazan sin guardar; los válidos crean, actualizan y eliminan (0) metas por ítem y cargo"""
        self.entrar("coordinador")
        clave = f"meta_{self.item.pk}_GESTOR_SOCIAL"
        r = self.client.post(f"/trimestres/{self.trimestre.pk}/metas/", {clave: "-3"})
        self.assertMensaje(r, "error", "número entero")
        self.client.post(f"/trimestres/{self.trimestre.pk}/metas/", {clave: "25", f"meta_{self.item_ges.pk}_DELEGADO": "4"})
        self.assertEqual(MetaTrimestre.objects.get(trimestre=self.trimestre, item=self.item, cargo="GESTOR_SOCIAL").cantidad, 25)
        self.assertTrue(MetaTrimestre.objects.filter(trimestre=self.trimestre, item=self.item_ges, cargo="DELEGADO").exists())
        self.client.post(f"/trimestres/{self.trimestre.pk}/metas/", {clave: "0"})
        self.assertFalse(MetaTrimestre.objects.filter(trimestre=self.trimestre, item=self.item).exists())

    def test_funcionario_no_administra_trimestres(self):
        """E3-Trimestres | Seguridad | Funcionario | Abrir trimestres y metas por URL | Responde 403"""
        self.entrar("funcionario")
        self.assertEqual(self.client.get("/trimestres/").status_code, 403)
        self.assertEqual(self.client.get(f"/trimestres/{self.trimestre.pk}/metas/").status_code, 403)

    def test_organizaciones(self):
        """E3-Organizaciones | JJVV y organizaciones | Delegado | Registrar una organización funcional y listar | Se crea con código ORG-00000 en la delegación activa; el listado solo muestra la delegación activa"""
        self.entrar("delegado")
        self.client.post("/organizaciones/nuevo/", {"nombre": "Club de Adulto Mayor Nueva Vida", "tipo": "ADULTO_MAYOR",
                                                    "delegacion": self.del01.pk, "comuna": "La Serena", "activo": "on"})
        o = Organizacion.objects.get(nombre="Club de Adulto Mayor Nueva Vida")
        self.assertRegex(o.codigo, r"^ORG-\d{5}$")
        r = self.client.get("/organizaciones/")
        self.assertContains(r, "Nueva Vida")
        self.assertNotContains(r, "Las Compañías Norte")


# =============================================================================
# Actividades y reglas de la matriz
# =============================================================================
class ActividadesTests(MatrizBase):
    def setUp(self):
        super().setUp()
        self.entrar("funcionario")

    def test_actividad_valida_suma_un_punto(self):
        """E3-Puntaje | Matriz de actividades | Funcionaria, trimestre abierto | Registrar una acción ejecutada con nombre y teléfono del vecino | Suma 1 punto, código SOC-00000 según el ámbito del ítem y responsable la funcionaria"""
        r = self.registrar()
        a = Actividad.objects.get()
        self.assertRedirects(r, f"/actividades/{a.pk}/")
        self.assertEqual(a.puntaje, 1)
        self.assertRegex(a.codigo, r"^SOC-\d{5}$")
        self.assertEqual((a.funcionario, a.delegacion, a.trimestre), (self.funcionaria, self.del01, self.trimestre))
        self.assertMensaje(r, "info", "suma 1 punto")

    def test_sin_nombre_o_telefono_no_suma(self):
        """E3-Puntaje | Matriz de actividades | Funcionaria | Registrar una actividad sin teléfono y otra sin nombre | Se guardan con 0 puntos y el motivo «Falta el nombre o el teléfono»"""
        self.registrar(telefono_contacto="")
        r = self.registrar(nombre_contacto="")
        self.assertEqual(list(Actividad.objects.values_list("puntaje", flat=True)), [0, 0])
        self.assertMensaje(r, "warning", "Falta el nombre o el teléfono")

    def test_coordinacion_previa_no_suma(self):
        """E3-Puntaje | Matriz de actividades | Funcionaria | Registrar una coordinación previa (correos, llamadas, invitaciones) | Queda registrada con 0 puntos: solo suma la acción ejecutada"""
        self.registrar(tipo_registro="COORDINACION")
        a = Actividad.objects.get()
        self.assertEqual(a.puntaje, 0)
        self.assertIn("Coordinación previa", a.motivo_sin_puntaje)

    def test_usuario_delegado_no_suma(self):
        """E3-Puntaje | Matriz de actividades | Funcionaria | Registrar una actividad cuyo solicitante es el propio delegado | Se registra como «otra gestión» con 0 puntos"""
        self.registrar(solicitante_tipo="DELEGADO")
        self.assertIn("otra gestión", Actividad.objects.get().motivo_sin_puntaje)

    def test_maximo_siete_por_dia(self):
        """E3-Límite diario | Matriz de actividades | Funcionaria con 6 actividades y 1 coordinación el mismo día | Registrar la octava del día | Se rechaza: máximo 7 por día (las coordinaciones también cuentan)"""
        for _ in range(6):
            self.registrar()
        self.registrar(tipo_registro="COORDINACION")
        r = self.registrar()
        self.assertContains(r, "el máximo diario es 7")
        self.assertEqual(Actividad.objects.filter(fecha=MIERCOLES).count(), 7)
        self.assertEqual(self.registrar(fecha="2026-11-17").status_code, 302)

    def test_fechas_no_validas(self):
        """E3-Cierre semanal | Matriz de actividades | Hoy miércoles 18-11-2026 | Registrar con fecha sábado, futura, fuera del trimestre y de la semana pasada (cerrada el lunes) | Se rechazan todas"""
        self.assertContains(self.registrar(fecha="2026-11-14"), "de lunes a viernes")
        self.assertContains(self.registrar(fecha="2026-11-19"), "fecha futura")
        self.assertContains(self.registrar(fecha="2026-11-13"), "está cerrada")
        Trimestre.objects.filter(pk=self.trimestre.pk).update(inicio=date(2026, 11, 17))
        self.assertContains(self.registrar(fecha="2026-11-16"), "fuera del trimestre")
        self.assertEqual(Actividad.objects.count(), 0)

    def test_semana_cierra_el_lunes_siguiente(self):
        """E3-Cierre semanal | Matriz de actividades | Actividad del viernes 13-11-2026 | Ingresarla el lunes 16 y luego el martes 17 | El lunes se acepta; desde el martes la semana está cerrada"""
        self.assertEqual(self.registrar(hoy=date(2026, 11, 16), fecha="2026-11-13").status_code, 302)
        r = self.registrar(hoy=date(2026, 11, 17), fecha="2026-11-13")
        self.assertContains(r, "está cerrada")

    def test_sin_trimestre_abierto(self):
        """E3-Trimestres | Matriz de actividades | Sin trimestre abierto | Registrar una actividad | Se rechaza indicando que no hay trimestre abierto"""
        Trimestre.objects.update(estado="CERRADO")
        self.assertContains(self.registrar(), "No hay un trimestre abierto")

    def test_eliminar_actividad_de_semana_cerrada(self):
        """E3-Cierre semanal | Matriz de actividades | Actividad del 16-11-2026 | Eliminarla el martes de la semana siguiente | Se rechaza: la semana está cerrada"""
        self.registrar(hoy=date(2026, 11, 16), fecha="2026-11-16")
        a = Actividad.objects.get()
        with hoy_es(date(2026, 11, 24)):
            r = self.client.post(f"/actividades/{a.pk}/eliminar/")
        self.assertMensaje(r, "error", "semana")
        self.assertTrue(Actividad.objects.filter(pk=a.pk).exists())

    def test_felicitacion_solo_delegado(self):
        """E3-Felicitaciones | Matriz de actividades | Funcionaria | Registrar en el ítem «Felicitaciones formales» | El ítem no está disponible para el funcionario y el servidor lo rechaza"""
        self.assertNotContains(self.client.get("/actividades/nuevo/"), "Felicitaciones formales")
        r = self.registrar(item=self.felicitacion.pk, respaldo=pdf(), destinatario=self.funcionaria.pk)
        self.assertContains(r, "Escoja una opción válida")
        self.assertEqual(Actividad.objects.count(), 0)


class FelicitacionesTests(MatrizBase):
    def test_delegado_valida_felicitacion_con_respaldo(self):
        """E3-Felicitaciones | Matriz de actividades | Delegada de DEL-00001 | Registrar una felicitación sin respaldo y luego con respaldo formal para la funcionaria | Sin respaldo se rechaza; con respaldo suma 1 punto a la funcionaria felicitada"""
        self.entrar("delegado")
        r = self.registrar(item=self.felicitacion.pk, destinatario=self.funcionaria.pk)
        self.assertContains(r, "Adjunte el respaldo formal")
        r = self.registrar(item=self.felicitacion.pk, destinatario=self.funcionaria.pk, respaldo=pdf())
        a = Actividad.objects.get()
        self.assertEqual((a.funcionario, a.registrado_por.username, a.puntaje), (self.funcionaria, "delegado", 1))
        self.assertEqual(self.client.get(f"/actividades/{a.pk}/respaldo/").status_code, 200)


# =============================================================================
# Ausencias y semáforo
# =============================================================================
class SemaforoTests(MatrizBase):
    def crear(self, n, item=None, puntaje=1):
        for i in range(n):
            Actividad.objects.create(trimestre=self.trimestre, funcionario=self.funcionaria,
                                     registrado_por=self.funcionaria, delegacion=self.del01, item=item or self.item,
                                     fecha=date(2026, 11, 2 + i % 5), descripcion="x", puntaje=puntaje)

    def test_cumplimiento_y_colores(self):
        """E3-Semáforo | Cálculo | Meta 10 en «Visitas en terreno» | Registrar 6, luego 8 y luego 15 actividades válidas | 60 % rojo, 80 % amarillo y 120 % verde (tope), con aviso de puntos sobre el tope"""
        self.crear(6)
        r = semaforo.resumen_funcionario(self.funcionaria, self.trimestre)
        self.assertEqual((r["items"][0]["cumplimiento"], r["color"]), (0.6, "ROJO"))
        self.crear(2)
        self.assertEqual(semaforo.resumen_funcionario(self.funcionaria, self.trimestre)["color"], "AMARILLO")
        self.crear(7)
        i = semaforo.resumen_funcionario(self.funcionaria, self.trimestre)["items"][0]
        self.assertEqual((i["cumplimiento"], i["color"], i["sobre_tope"], i["puntos_sobre_tope"]), (1.2, "VERDE", True, 3))

    def test_actividades_sin_puntaje_no_cuentan(self):
        """E3-Semáforo | Cálculo | Meta 10 | Registrar 10 actividades sin puntaje (coordinaciones) | El cumplimiento es 0 %"""
        self.crear(10, puntaje=0)
        self.assertEqual(semaforo.resumen_funcionario(self.funcionaria, self.trimestre)["total"], 0)

    def test_ausencias_ajustan_la_meta(self):
        """E3-Ausencias | Semáforo | Trimestre con 66 días hábiles y meta 10 | Delegado ingresa 11 días hábiles de vacaciones | La meta se ajusta a 8,3 y el cumplimiento se recalcula"""
        self.assertEqual(self.trimestre.dias_habiles, 66)
        self.entrar("delegado")
        r = self.client.post("/ausencias/nuevo/", {"funcionario": self.funcionaria.pk, "tipo": "VACACIONES",
                                                   "desde": "2026-11-02", "hasta": "2026-11-16"})
        self.assertEqual(r.status_code, 302)
        resumen = semaforo.resumen_funcionario(self.funcionaria, self.trimestre)
        self.assertEqual((resumen["dias_ausencia"], resumen["items"][0]["meta_ajustada"]), (11, 8.3))
        self.assertEqual(Ausencia.objects.get().registrado_por.username, "delegado")

    def test_reglas_de_ausencias(self):
        """E3-Ausencias | Ausencias | Delegado y funcionaria | Registrar con fechas invertidas, superpuestas y como funcionaria | Se rechazan las fechas inválidas y el funcionario no tiene acceso (403)"""
        self.entrar("delegado")
        r = self.client.post("/ausencias/nuevo/", {"funcionario": self.funcionaria.pk, "tipo": "LICENCIA",
                                                   "desde": "2026-11-10", "hasta": "2026-11-05"})
        self.assertContains(r, "no puede ser anterior")
        self.client.post("/ausencias/nuevo/", {"funcionario": self.funcionaria.pk, "tipo": "LICENCIA",
                                               "desde": "2026-11-05", "hasta": "2026-11-10"})
        r = self.client.post("/ausencias/nuevo/", {"funcionario": self.funcionaria.pk, "tipo": "DIA_LIBRE",
                                                   "desde": "2026-11-09", "hasta": "2026-11-09"})
        self.assertContains(r, "Se superpone")
        self.client.logout()
        self.entrar("funcionario")
        self.assertEqual(self.client.get("/ausencias/nuevo/").status_code, 403)

    def test_dashboards_por_rol(self):
        """E3-Dashboards | Dashboards | Datos de prueba | Abrir las tres vistas con superadmin, delegado y funcionario | Cada rol ve solo las vistas autorizadas; el delegado ve a su equipo y no a funcionarios de otra delegación"""
        self.crear(5)
        self.entrar("superadmin")
        r = self.client.get(f"/dashboard/general/?trimestre={self.trimestre.pk}")
        self.assertContains(r, "Delegación Centro")
        self.assertEqual(len(r.context["resumen"]["delegaciones"]), Delegacion.objects.filter(activo=True).count())
        self.client.logout()
        self.entrar("delegado")
        self.assertEqual(self.client.get("/dashboard/general/").status_code, 403)
        r = self.client.get(f"/dashboard/delegacion/?trimestre={self.trimestre.pk}")
        self.assertContains(r, "Fernanda Funcionaria")
        r = self.client.get(f"/dashboard/funcionario/?funcionario={self.funcionaria.pk}&trimestre={self.trimestre.pk}")
        self.assertEqual(r.context["resumen"]["items"][0]["puntos"], 5)
        otro = Usuario.objects.get(username="funcionario2")
        self.assertEqual(self.client.get(f"/dashboard/funcionario/?funcionario={otro.pk}").status_code, 404)
        self.client.logout()
        self.entrar("funcionario")
        self.assertEqual(self.client.get("/dashboard/delegacion/").status_code, 403)
        self.assertEqual(self.client.get("/dashboard/funcionario/").status_code, 200)
        delegada = Usuario.objects.get(username="delegado")
        self.assertEqual(self.client.get(f"/dashboard/funcionario/?funcionario={delegada.pk}").status_code, 403)

    def test_vision_de_equipo_por_delegacion(self):
        """E3-Dashboards | Semáforo por delegación | Meta 10 de la funcionaria y 10 de otra Gestora Social | Registrar 15 puntos solo a la funcionaria | El ítem de la delegación suma puntos y metas del equipo: 75 % (amarillo)"""
        otra = Usuario.objects.create_user("gestora2", "gestora2@sgr.test", CLAVE, nombre="Gabriela Gestora",
                                           rol=Rol.objects.get(nombre="Funcionario"), cargo="GESTOR_SOCIAL")
        otra.delegaciones.set([self.del01])
        self.crear(15)
        r = semaforo.resumen_delegacion(self.del01, self.trimestre)
        fila = next(i for i in r["items"] if i["item"] == self.item)
        self.assertEqual((fila["puntos"], fila["meta_ajustada"], fila["cumplimiento"]), (15, 20.0, 0.75))


# =============================================================================
# Tubo de trabajo, evidencias y API
# =============================================================================
class TuboTests(MatrizBase):
    def crear_compromiso(self, **extra):
        datos = {"titulo": "Revisión de luminarias", "solicitante": "Marta Henríquez",
                 "responsable": self.funcionaria.pk, "descripcion": "Dos luminarias apagadas."}
        datos.update(extra)
        self.client.post("/tubo/nuevo/", datos)
        return Compromiso.objects.latest("pk")

    def test_flujo_completo_con_evidencia(self):
        """E3-Tubo | Tubo de trabajo | Funcionaria y delegada | Ingresar compromiso, avanzar a Pendiente y En proceso, intentar Realizar sin evidencia, subir foto, aprobarla y realizar | Código TUB, historial de cada estado; Realizar solo con evidencia aprobada"""
        self.entrar("funcionario")
        c = self.crear_compromiso()
        self.assertRegex(c.codigo, r"^TUB-\d{5}$")
        self.assertEqual((c.estado, c.delegacion, c.creado_por), ("INGRESADO", self.del01, self.funcionaria))
        self.client.post(f"/tubo/{c.pk}/avanzar/")
        self.client.post(f"/tubo/{c.pk}/avanzar/")
        r = self.client.post(f"/tubo/{c.pk}/avanzar/")
        self.assertMensaje(r, "error", "evidencia fotográfica aprobada")
        r = self.client.post(f"/tubo/{c.pk}/evidencias/", {"foto": png(), "descripcion": "Luminaria reparada"})
        self.assertMensaje(r, "success", "pendiente de revisión")
        e = Evidencia.objects.get()
        self.assertEqual(self.client.post(f"/tubo/{c.pk}/evidencias/{e.pk}/revisar/", {"decision": "aprobar"}).status_code, 403)
        self.client.logout()
        self.entrar("delegado")
        self.client.post(f"/tubo/{c.pk}/evidencias/{e.pk}/revisar/", {"decision": "aprobar"})
        self.client.post(f"/tubo/{c.pk}/avanzar/")
        c.refresh_from_db()
        self.assertEqual(c.estado, "REALIZADO")
        self.assertEqual(list(c.historial.order_by("pk").values_list("estado_nuevo", flat=True)),
                         ["INGRESADO", "PENDIENTE", "EN_PROCESO", "REALIZADO"])
        self.assertEqual(self.client.get(f"/tubo/{c.pk}/evidencias/{e.pk}/foto/").status_code, 200)

    def test_rechazo_y_archivos_invalidos(self):
        """E3-Evidencias | Tubo de trabajo | Compromiso ingresado | Subir un archivo que no es imagen; rechazar una foto sin y con motivo | El archivo se rechaza; el rechazo exige motivo y deja la foto rechazada"""
        self.entrar("delegado")
        c = self.crear_compromiso()
        falso = SimpleUploadedFile("foto.jpg", b"no es una imagen", content_type="image/jpeg")
        r = self.client.post(f"/tubo/{c.pk}/evidencias/", {"foto": falso})
        self.assertMensaje(r, "error", "no es una imagen válida")
        self.client.post(f"/tubo/{c.pk}/evidencias/", {"foto": png()})
        e = Evidencia.objects.get()
        r = self.client.post(f"/tubo/{c.pk}/evidencias/{e.pk}/revisar/", {"decision": "rechazar"})
        self.assertMensaje(r, "error", "motivo del rechazo")
        self.client.post(f"/tubo/{c.pk}/evidencias/{e.pk}/revisar/", {"decision": "rechazar", "comentario": "Foto borrosa"})
        e.refresh_from_db()
        self.assertEqual((e.estado, e.comentario_revision), ("RECHAZADA", "Foto borrosa"))

    def test_tablero_indicadores_y_alcance(self):
        """E3-Tubo | Tablero Kanban | Compromisos en DEL-00001 y uno en DEL-00002 | Abrir el tablero como funcionaria de DEL-00001 y abrir por URL el de otra delegación | Indicadores y columnas solo de su delegación; el ajeno responde 404"""
        self.entrar("delegado")
        c = self.crear_compromiso()
        self.client.post(f"/tubo/{c.pk}/avanzar/")
        ajeno = Compromiso.objects.create(titulo="Ajeno", solicitante="x", delegacion=self.del02,
                                          responsable=Usuario.objects.get(username="funcionario2"),
                                          creado_por=Usuario.objects.get(username="delegado2"))
        self.client.logout()
        self.entrar("funcionario")
        r = self.client.get("/tubo/")
        self.assertEqual(r.context["indicadores"]["total"], 1)
        self.assertEqual(r.context["indicadores"]["pendientes"], 1)
        self.assertEqual([len(col["items"]) for col in r.context["columnas"]], [0, 1, 0, 0])
        self.assertEqual(self.client.get(f"/tubo/{ajeno.pk}/").status_code, 404)

    def test_derivar_actividad_al_tubo(self):
        """E3-Tubo | Matriz → Tubo | Actividad registrada por la funcionaria | Derivarla al tubo | El formulario se precarga y el compromiso muestra la referencia SOC de la actividad"""
        self.entrar("funcionario")
        self.registrar()
        a = Actividad.objects.get()
        r = self.client.get(f"/tubo/nuevo/?actividad={a.pk}")
        self.assertContains(r, a.codigo)
        self.client.post("/tubo/nuevo/", {"actividad": a.pk, "titulo": f"[{a.codigo}] Visita", "solicitante": "Marta",
                                          "responsable": self.funcionaria.pk})
        c = Compromiso.objects.get()
        self.assertEqual((c.actividad, c.referencia), (a, a.codigo))


class ApiMovilTests(MatrizBase):
    def token(self, usuario="funcionario", clave=CLAVE):
        r = self.client.post("/api/v1/token/", json.dumps({"identificador": usuario, "clave": clave}),
                             content_type="application/json")
        return r

    def test_api_token_listado_y_evidencia(self):
        """E3-API móvil | API REST | Compromiso asignado a la funcionaria | Pedir token, listar compromisos y subir una foto de evidencia | Token 201; listado solo de su delegación; evidencia registrada con origen App móvil"""
        responsable = self.funcionaria
        c = Compromiso.objects.create(titulo="Poda", solicitante="JJVV", delegacion=self.del01, responsable=responsable,
                                      creado_por=responsable)
        Compromiso.objects.create(titulo="Ajeno", solicitante="x", delegacion=self.del02, responsable=responsable,
                                  creado_por=responsable)
        r = self.token()
        self.assertEqual(r.status_code, 201)
        cabecera = {"HTTP_AUTHORIZATION": f"Token {r.json()['token']}"}
        datos = self.client.get("/api/v1/compromisos/", **cabecera).json()
        self.assertEqual([x["codigo"] for x in datos["resultados"]], [c.codigo])
        r = self.client.post(f"/api/v1/compromisos/{c.pk}/evidencias/", {"foto": png(), "descripcion": "Desde la app"},
                             **cabecera)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Evidencia.objects.get().origen, "APP")
        self.assertEqual(self.client.get(f"/api/v1/compromisos/{c.pk}/", **cabecera).json()["evidencias"][0]["estado"],
                         "PENDIENTE")

    def test_api_seguridad(self):
        """E3-API móvil | API REST | Sin token, token inválido, clave errónea y usuario con clave provisoria | Llamar a la API | Responde 401, 401, 401 y 403 respectivamente; el token se guarda solo como hash"""
        self.assertEqual(self.client.get("/api/v1/compromisos/").status_code, 401)
        self.assertEqual(self.client.get("/api/v1/compromisos/", HTTP_AUTHORIZATION="Token falso").status_code, 401)
        self.assertEqual(self.token(clave="Mala.123").status_code, 401)
        r = self.token()
        clave = r.json()["token"]
        self.assertFalse(TokenApi.objects.filter(clave_hash=clave).exists())
        Usuario.objects.filter(username="funcionario").update(debe_cambiar_clave=True)
        self.assertEqual(self.token().status_code, 403)
        self.assertEqual(self.client.get("/api/v1/compromisos/", HTTP_AUTHORIZATION=f"Token {clave}").status_code, 403)


class PermisosRolesTests(PruebaSGR):
    def test_migracion_agrega_permisos_nuevos(self):
        """E3-Roles | Migración de permisos | Rol Delegado con permisos antiguos (incluye seguimiento.ver) | Ejecutar la migración de permisos de la Etapa 3 | Recibe los permisos de los módulos nuevos, conserva los suyos y pierde «seguimiento»"""
        rol = Rol.objects.get(nombre="Delegado municipal")
        rol.permisos = ["inicio.ver", "atenciones.ver", "seguimiento.ver"]
        rol.save()
        importlib.import_module("matriz.migrations.0002_permisos_roles").actualizar(registro, None)
        rol.refresh_from_db()
        self.assertIn("actividades.aprobar", rol.permisos)
        self.assertIn("atenciones.ver", rol.permisos)
        self.assertNotIn("seguimiento.ver", rol.permisos)
