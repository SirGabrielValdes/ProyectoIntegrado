"""
Carga datos de prueba ficticios para la demostración y las pruebas de la entrega.

    python manage.py cargar_datos_demo            # crea o actualiza (idempotente)
    python manage.py cargar_datos_demo --atenciones 500   # volumen para pruebas de estrés

La contraseña de los usuarios de prueba se toma de la variable SGR_CLAVE_DEMO
(por defecto «Serena.2026»). Úsela solo en ambientes de prueba.
"""
import os
import random

from django.core.management.base import BaseCommand
from django.db import transaction

from atenciones.models import Atencion, Vecino
from catalogos.models import Delegacion, Item, SubAtencion, TipoAtencion
from core.permisos import ROLES_BASE
from core.validadores import digito_verificador
from cuentas.models import Rol, Usuario

DELEGACIONES = [
    ("DEL01", "Delegación Centro", "Arturo Prat 451"),
    ("DEL02", "Delegación Las Compañías", "Av. Cisternas 1650"),
    ("DEL03", "Delegación Antena", "Av. Balmaceda 3201"),
    ("DEL04", "Delegación La Pampa", "Larraín Alcalde 2450"),
    ("DEL05", "Delegación Avenida del Mar", "Av. del Mar 3800"),
    ("DEL06", "Delegación Pedro Aguirre Cerda", "Av. Pedro Aguirre Cerda 1200"),
    ("DEL07", "Delegación Rural", "Ruta D-41, km 12"),
]

TIPOS = {
    ("TA01", "Social", "Ayudas y orientación social a vecinos."): [
        ("SA01", "Ayuda social"), ("SA02", "Orientación en beneficios"), ("SA03", "Registro Social de Hogares")],
    ("TA02", "Infraestructura", "Requerimientos de espacios públicos y vialidad."): [
        ("SA04", "Luminaria pública"), ("SA05", "Bacheo y veredas"), ("SA06", "Áreas verdes")],
    ("TA03", "Aseo y ornato", "Retiro de residuos y limpieza."): [
        ("SA07", "Retiro de voluminosos"), ("SA08", "Microbasural")],
    ("TA04", "Seguridad", "Seguridad ciudadana y convivencia."): [
        ("SA09", "Patrullaje preventivo"), ("SA10", "Cámaras de vigilancia")],
    ("TA05", "Trámites", "Orientación sobre trámites municipales."): [
        ("SA11", "Permisos y patentes"), ("SA12", "Certificados")],
}

USUARIOS = [
    ("superadmin", "Sofía Superadmin", "superadmin@sgr.test", "SUPERADMIN", ["DEL01"], True),
    ("coordinador", "Carlos Coordinador", "coordinador@sgr.test", "COORDINADOR", ["DEL01", "DEL02", "DEL03"], True),
    ("delegado", "Daniela Delegada", "delegado@sgr.test", "DELEGADO", ["DEL01"], True),
    ("delegado2", "Diego Delegado", "delegado2@sgr.test", "DELEGADO", ["DEL02"], True),
    ("funcionario", "Fernanda Funcionaria", "funcionario@sgr.test", "FUNCIONARIO", ["DEL01"], True),
    ("funcionario2", "Felipe Funcionario", "funcionario2@sgr.test", "FUNCIONARIO", ["DEL02"], True),
    ("inactivo", "Ignacio Inactivo", "inactivo@sgr.test", "FUNCIONARIO", ["DEL01"], False),
]

NOMBRES = ["Ana", "Benjamín", "Camila", "Diego", "Elena", "Francisco", "Gabriela", "Héctor", "Isidora", "Joaquín",
           "Karina", "Luis", "María", "Nicolás", "Olga", "Pablo", "Rocío", "Sebastián", "Teresa", "Vicente"]
APELLIDOS = ["Araya", "Bravo", "Castillo", "Díaz", "Espinoza", "Flores", "González", "Herrera", "Rojas", "Muñoz",
             "Pizarro", "Rivera", "Soto", "Tapia", "Vega", "Alfaro", "Cortés", "Olivares"]


class Command(BaseCommand):
    help = "Carga datos de prueba ficticios (delegaciones, roles, usuarios, catálogos, vecinos y atenciones)."

    def add_arguments(self, parser):
        parser.add_argument("--atenciones", type=int, default=40, help="Cantidad de atenciones de ejemplo.")
        parser.add_argument("--vecinos", type=int, default=60)

    @transaction.atomic
    def handle(self, *args, **opciones):
        random.seed(2026)
        clave = os.environ.get("SGR_CLAVE_DEMO", "Serena.2026")

        delegaciones = {}
        for codigo, nombre, direccion in DELEGACIONES:
            delegaciones[codigo], _ = Delegacion.objects.update_or_create(
                codigo=codigo, defaults={"nombre": nombre, "direccion": direccion, "comuna": "La Serena"})

        roles = {}
        for clave_rol, datos in ROLES_BASE.items():
            rol, _ = Rol.objects.update_or_create(codigo=datos["codigo"], defaults={
                "nombre": datos["nombre"], "descripcion": datos["descripcion"], "alcance": datos["alcance"],
                "permisos": datos["permisos"], "activo": True})
            if rol.es_sistema != datos["es_sistema"]:
                Rol.objects.filter(pk=rol.pk).update(es_sistema=datos["es_sistema"])
            roles[clave_rol] = rol

        # SGR_CORREO_ADMIN: correo real del superadmin (p. ej. el personal del encargado),
        # para recibir el código de recuperación. Se define solo en el .env del servidor.
        correo_admin = os.environ.get("SGR_CORREO_ADMIN", "").strip().lower()
        usuarios = []
        for username, nombre, correo, rol, dels, activo in USUARIOS:
            if username == "superadmin" and correo_admin:
                correo = correo_admin
            u = Usuario.objects.filter(username=username).first() or Usuario(username=username)
            u.nombre, u.correo, u.rol, u.is_active = nombre, correo, roles[rol], activo
            u.set_password(clave)
            u.save()
            u.delegaciones.set([delegaciones[d] for d in dels])
            usuarios.append(u)

        for i in range(1, 26):
            Item.objects.update_or_create(codigo=f"IT{i:02d}", defaults={
                "nombre": f"Meta de gestión {i:02d}",
                "descripcion": f"Ítem de ejemplo N° {i} para el seguimiento de metas del proyecto.",
                "activo": i % 7 != 0})

        subs = []
        for (codigo, nombre, descripcion), lista in TIPOS.items():
            tipo, _ = TipoAtencion.objects.update_or_create(codigo=codigo, defaults={
                "nombre": nombre, "descripcion": descripcion, "activo": True})
            for cod_sub, nom_sub in lista:
                s, _ = SubAtencion.objects.update_or_create(codigo=cod_sub, defaults={
                    "nombre": nom_sub, "tipo": tipo, "activo": True})
                subs.append(s)
        TipoAtencion.objects.update_or_create(codigo="TA06", defaults={
            "nombre": "Cultura (inactivo)", "descripcion": "Tipo inactivo para pruebas.", "activo": False})

        vecinos = list(Vecino.objects.all())
        base = 10_000_000 + Vecino.objects.count()
        while len(vecinos) < opciones["vecinos"]:
            cuerpo = base + len(vecinos) * 7919
            nombre = f"{random.choice(NOMBRES)} {random.choice(APELLIDOS)} {random.choice(APELLIDOS)}"
            v, _ = Vecino.objects.get_or_create(rut=f"{cuerpo}{digito_verificador(cuerpo)}", defaults={
                "nombre": nombre, "telefono": f"+56 9 {random.randint(1000, 9999)} {random.randint(1000, 9999)}",
                "correo": f"vecino{len(vecinos) + 1}@correo.test"})
            vecinos.append(v)

        operadores = [u for u in usuarios if u.is_active and u.rol.alcance != "GLOBAL"]
        faltan = opciones["atenciones"] - Atencion.objects.count()
        nuevas = []
        for _ in range(max(0, faltan)):
            u = random.choice(operadores)
            s = random.choice(subs)
            nuevas.append(Atencion(
                vecino=random.choice(vecinos), tipo=s.tipo, subatencion=s, delegacion=u.delegaciones.first(),
                responsable=u, descripcion=f"Solicitud de ejemplo sobre {s.nombre.lower()}. Datos ficticios."))
        Atencion.objects.bulk_create(nuevas, batch_size=500)

        self.stdout.write(self.style.SUCCESS(
            f"Datos de prueba listos: {Delegacion.objects.count()} delegaciones, {Rol.objects.count()} roles, "
            f"{Usuario.objects.count()} usuarios, {Item.objects.count()} ítems, {TipoAtencion.objects.count()} tipos, "
            f"{SubAtencion.objects.count()} sub atenciones, {Vecino.objects.count()} vecinos, "
            f"{Atencion.objects.count()} atenciones."))
        self.stdout.write("Usuarios de prueba: " + ", ".join(u[0] for u in USUARIOS) + " (clave: SGR_CLAVE_DEMO).")
