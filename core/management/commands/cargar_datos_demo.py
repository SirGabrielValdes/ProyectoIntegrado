"""
Carga datos de prueba ficticios para la demostración y las pruebas de la entrega.

    python manage.py cargar_datos_demo                    # crea o actualiza (idempotente)
    python manage.py cargar_datos_demo --atenciones 500   # volumen para pruebas de estrés

Los códigos (DEL-00001, ITM-00003, TUB-00010…) los asigna el sistema. La
contraseña de los usuarios de prueba se toma de SGR_CLAVE_DEMO (por defecto
«Serena.2026»). Úsela solo en ambientes de prueba.
"""
import os
import random
from datetime import date, timedelta
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageDraw

from atenciones.models import Atencion, Vecino
from catalogos.models import Delegacion, Item, SubAtencion, TipoAtencion
from core.permisos import ROLES_BASE
from core.validadores import digito_verificador
from cuentas.models import Rol, Usuario
from matriz.models import Actividad, Ausencia, MetaTrimestre, Organizacion, Trimestre
from matriz.reglas import MAX_ACTIVIDADES_DIA, calcular_puntaje
from tubo.models import AreaApoyo, Compromiso, Evidencia, HistorialCompromiso

DELEGACIONES = [
    ("Delegación Centro", "Arturo Prat 451"),
    ("Delegación Las Compañías", "Av. Cisternas 1650"),
    ("Delegación Antena", "Av. Balmaceda 3201"),
    ("Delegación La Pampa", "Larraín Alcalde 2450"),
    ("Delegación Avenida del Mar", "Av. del Mar 3800"),
    ("Delegación Pedro Aguirre Cerda", "Av. Pedro Aguirre Cerda 1200"),
    ("Delegación Rural", "Ruta D-41, km 12"),
]

TIPOS = {
    ("Social", "Ayudas y orientación social a vecinos."): [
        "Ayuda social", "Orientación en beneficios", "Registro Social de Hogares"],
    ("Infraestructura", "Requerimientos de espacios públicos y vialidad."): [
        "Luminaria pública", "Bacheo y veredas", "Áreas verdes"],
    ("Aseo y ornato", "Retiro de residuos y limpieza."): ["Retiro de voluminosos", "Microbasural"],
    ("Seguridad", "Seguridad ciudadana y convivencia."): ["Patrullaje preventivo", "Cámaras de vigilancia"],
    ("Trámites", "Orientación sobre trámites municipales."): ["Permisos y patentes", "Certificados"],
}

# Ítems de la matriz basados en el «Descriptor de funciones para los cargos de las Delegaciones».
ITEMS = [
    ("Atención y evaluación de casos sociales", "SOC", "Recepción, evaluación, diagnóstico e intervención de casos."),
    ("Visitas en terreno", "SOC", "Visitas domiciliarias o a sectores para levantar necesidades."),
    ("Derivación y articulación con redes de apoyo", "SOC", "Derivación a programas y servicios municipales."),
    ("Visitas a Juntas de Vecinos y organizaciones", "GES", "Presencia, acompañamiento y apoyo a dirigentes."),
    ("Talleres y actividades con organizaciones", "GES", "Talleres, capacitaciones y actividades comunitarias."),
    ("Asesoría a organizaciones comunitarias", "GES", "Formación, legalización y vigencia de OOCC."),
    ("Operativos de limpieza y desmalezado", "GES", "Operativos con cuadrillas en bienes nacionales de uso público."),
    ("Educación ambiental y reciclaje", "GES", "Talleres de reciclaje, compostaje, aseo y ornato."),
    ("Atención de público y registro de solicitudes", "GES", "Atención presencial y registro en la planilla SGR."),
    ("Mesas de trabajo y coordinación territorial", "GES", "Mesas con estamentos públicos y privados."),
    ("Difusión de programas municipales", "GES", "Difusión de programas y actividades del municipio."),
    ("Felicitaciones formales", "GES", "Felicitaciones de usuarios con respaldo formal (solo las registra el delegado)."),
]

METAS = {  # cargo -> {índice de ítem: meta trimestral}
    "DELEGADO": {3: 12, 9: 6, 11: 3},
    "GESTOR_SOCIAL": {0: 30, 1: 20, 2: 15},
    "ORGANIZACIONES": {3: 20, 4: 12, 5: 15},
    "APOYO_ADMINISTRATIVO": {8: 40, 10: 10},
    "SERVICIOS_COMUNITARIOS": {6: 15, 7: 10},
    "GESTION_PLANIFICACION": {9: 10, 10: 12},
    "COMPRAS_PROYECTOS": {9: 8},
}

USUARIOS = [  # usuario, nombre, correo, rol, cargo, delegaciones (índices), activo
    ("superadmin", "Sofía Superadmin", "superadmin@sgr.test", "SUPERADMIN", "", [0], True),
    ("coordinador", "Carlos Coordinador", "coordinador@sgr.test", "COORDINADOR", "", [0, 1, 2], True),
    ("delegado", "Daniela Delegada", "delegado@sgr.test", "DELEGADO", "DELEGADO", [0], True),
    ("delegado2", "Diego Delegado", "delegado2@sgr.test", "DELEGADO", "DELEGADO", [1], True),
    ("funcionario", "Fernanda Funcionaria", "funcionario@sgr.test", "FUNCIONARIO", "GESTOR_SOCIAL", [0], True),
    ("funcionario2", "Felipe Funcionario", "funcionario2@sgr.test", "FUNCIONARIO", "ORGANIZACIONES", [1], True),
    ("apoyo", "Andrea Apoyo", "apoyo@sgr.test", "FUNCIONARIO", "APOYO_ADMINISTRATIVO", [0], True),
    ("servicios", "Sergio Servicios", "servicios@sgr.test", "FUNCIONARIO", "SERVICIOS_COMUNITARIOS", [0], True),
    ("planificacion", "Paula Planificación", "planificacion@sgr.test", "FUNCIONARIO", "GESTION_PLANIFICACION", [1], True),
    ("inactivo", "Ignacio Inactivo", "inactivo@sgr.test", "FUNCIONARIO", "APOYO_ADMINISTRATIVO", [0], False),
]

AREAS = ["Obras Municipales", "Dirección de Tránsito", "Parques y Jardines", "Aseo y Ornato",
         "Desarrollo Comunitario (DIDECO)", "Seguridad Ciudadana"]

ORGANIZACIONES = [  # nombre, tipo, delegación
    ("Junta de Vecinos Terrazas del Brillador", "JJVV", 0), ("Junta de Vecinos El Brillador", "JJVV", 0),
    ("Club de Adulto Mayor Renacer", "ADULTO_MAYOR", 0), ("Club Deportivo Juventud Centro", "DEPORTIVA", 0),
    ("Centro de Madres Las Rosas", "CULTURAL", 0), ("Comité de Seguridad Pasaje Las Rosas", "COMITE", 0),
    ("Junta de Vecinos Las Compañías Norte", "JJVV", 1), ("Club de Adulto Mayor Los Aromos", "ADULTO_MAYOR", 1),
    ("Agrupación Juvenil Compañías Activa", "CULTURAL", 1), ("Comité de Allegados Esperanza", "COMITE", 1),
    ("Junta de Vecinos Antena Sur", "JJVV", 2), ("Club Deportivo La Pampa Unida", "DEPORTIVA", 3),
]

COMPROMISOS = [  # título, solicitante, área, estado
    ("Revisión de luminarias en Pasaje Las Rosas", "Marta Henríquez", 0, "INGRESADO"),
    ("Instalación de reductores de velocidad en Av. Islón", "Junta de Vecinos El Brillador", 1, "INGRESADO"),
    ("Evaluación social y derivación para canasta de alimentos", "Beatriz Ossa Manríquez", 4, "INGRESADO"),
    ("Salida a terreno y catastro con dirigentes", "Delegación", 0, "PENDIENTE"),
    ("Solicitud de poda JJVV Terrazas del Brillador", "JJVV Terrazas del Brillador", 2, "EN_PROCESO"),
    ("Solicitud de información de subsidios", "Vecino del sector", 4, "REALIZADO"),
    ("Retiro de microbasural en calle Los Pinos", "Comité de Seguridad Pasaje Las Rosas", 3, "REALIZADO"),
    ("Reparación de veredas frente a sede vecinal", "Junta de Vecinos El Brillador", 0, "REALIZADO"),
]

NOMBRES = ["Ana", "Benjamín", "Camila", "Diego", "Elena", "Francisco", "Gabriela", "Héctor", "Isidora", "Joaquín",
           "Karina", "Luis", "María", "Nicolás", "Olga", "Pablo", "Rocío", "Sebastián", "Teresa", "Vicente"]
APELLIDOS = ["Araya", "Bravo", "Castillo", "Díaz", "Espinoza", "Flores", "González", "Herrera", "Rojas", "Muñoz",
             "Pizarro", "Rivera", "Soto", "Tapia", "Vega", "Alfaro", "Cortés", "Olivares"]


def trimestre_de(fecha):
    n = (fecha.month - 1) // 3 + 1
    inicio = date(fecha.year, 3 * n - 2, 1)
    fin = date(fecha.year + (n == 4), (3 * n) % 12 + 1, 1) - timedelta(days=1)
    return n, inicio, fin


def foto_demo(texto):
    imagen = Image.new("RGB", (640, 420), (200, 200, 200))
    dibujo = ImageDraw.Draw(imagen)
    dibujo.rectangle([20, 20, 620, 400], outline=(196, 18, 48), width=6)
    dibujo.text((40, 190), f"Evidencia de prueba · {texto}", fill=(40, 40, 40))
    salida = BytesIO()
    imagen.save(salida, "JPEG", quality=70)
    return ContentFile(salida.getvalue(), name=f"{texto.lower()}.jpg")


class Command(BaseCommand):
    help = "Carga datos de prueba ficticios (estructura, catálogos, matriz SGR y tubo de trabajo)."

    def add_arguments(self, parser):
        parser.add_argument("--atenciones", type=int, default=40, help="Cantidad de atenciones de ejemplo.")
        parser.add_argument("--vecinos", type=int, default=60)
        parser.add_argument("--actividades", type=int, default=150, help="Actividades de la matriz (solo si no hay).")
        parser.add_argument("--sin-transacciones", action="store_true",
                            help="No crea actividades, ausencias ni compromisos (lo usan las pruebas).")

    @transaction.atomic
    def handle(self, *args, **opciones):
        random.seed(2026)
        clave = os.environ.get("SGR_CLAVE_DEMO", "Serena.2026")
        hoy = timezone.localdate()

        delegaciones = []
        for nombre, direccion in DELEGACIONES:
            d, _ = Delegacion.objects.update_or_create(nombre=nombre, defaults={
                "direccion": direccion, "comuna": "La Serena"})
            delegaciones.append(d)

        roles = {}
        for clave_rol, datos in ROLES_BASE.items():
            rol, _ = Rol.objects.update_or_create(nombre=datos["nombre"], defaults={
                "descripcion": datos["descripcion"], "alcance": datos["alcance"],
                "permisos": datos["permisos"], "activo": True})
            if rol.es_sistema != datos["es_sistema"]:
                Rol.objects.filter(pk=rol.pk).update(es_sistema=datos["es_sistema"])
            roles[clave_rol] = rol

        # SGR_CORREO_ADMIN: correo real del superadmin para recibir el código de recuperación.
        correo_admin = os.environ.get("SGR_CORREO_ADMIN", "").strip().lower()
        usuarios = {}
        for username, nombre, correo, rol, cargo, dels, activo in USUARIOS:
            if username == "superadmin" and correo_admin:
                correo = correo_admin
            u = Usuario.objects.filter(username=username).first() or Usuario(username=username)
            u.nombre, u.correo, u.rol, u.cargo, u.is_active = nombre, correo, roles[rol], cargo, activo
            u.debe_cambiar_clave = False
            u.set_password(clave)
            u.save()
            u.delegaciones.set([delegaciones[i] for i in dels])
            usuarios[username] = u

        items = []
        for nombre, ambito, descripcion in ITEMS:
            item, _ = Item.objects.update_or_create(nombre=nombre, defaults={
                "ambito": ambito, "descripcion": descripcion, "activo": True,
                "es_felicitacion": nombre == "Felicitaciones formales"})
            items.append(item)

        subs = []
        for (nombre, descripcion), lista in TIPOS.items():
            tipo, _ = TipoAtencion.objects.update_or_create(nombre=nombre, defaults={
                "descripcion": descripcion, "activo": True})
            for nom_sub in lista:
                s, _ = SubAtencion.objects.update_or_create(nombre=nom_sub, tipo=tipo, defaults={"activo": True})
                subs.append(s)
        TipoAtencion.objects.update_or_create(nombre="Cultura (inactivo)", defaults={
            "descripcion": "Tipo inactivo para pruebas.", "activo": False})

        areas = [AreaApoyo.objects.update_or_create(nombre=n, defaults={"activo": True})[0] for n in AREAS]
        organizaciones = []
        for nombre, tipo, d in ORGANIZACIONES:
            o, _ = Organizacion.objects.update_or_create(nombre=nombre, defaults={
                "tipo": tipo, "delegacion": delegaciones[d], "dirigente": f"{random.choice(NOMBRES)} {random.choice(APELLIDOS)}",
                "telefono": f"+56 9 {random.randint(1000, 9999)} {random.randint(1000, 9999)}", "activo": True})
            organizaciones.append(o)

        # Trimestre en curso (abierto) y el anterior (cerrado), con metas por cargo.
        n, inicio, fin = trimestre_de(hoy)
        n_ant, inicio_ant, fin_ant = trimestre_de(inicio - timedelta(days=1))
        Trimestre.objects.filter(estado="ABIERTO").exclude(inicio=inicio).update(estado="CERRADO")
        anterior, _ = Trimestre.objects.update_or_create(inicio=inicio_ant, defaults={
            "nombre": f"{n_ant}.º trimestre {inicio_ant.year}", "fin": fin_ant, "estado": "CERRADO"})
        actual, _ = Trimestre.objects.update_or_create(inicio=inicio, defaults={
            "nombre": f"{n}.º trimestre {inicio.year}", "fin": fin, "estado": "ABIERTO"})
        for t in (anterior, actual):
            for cargo, metas in METAS.items():
                for i, cantidad in metas.items():
                    MetaTrimestre.objects.update_or_create(trimestre=t, item=items[i], cargo=cargo,
                                                           defaults={"cantidad": cantidad})

        vecinos = list(Vecino.objects.all())
        base = 10_000_000 + Vecino.objects.count()
        while len(vecinos) < opciones["vecinos"]:
            cuerpo = base + len(vecinos) * 7919
            nombre = f"{random.choice(NOMBRES)} {random.choice(APELLIDOS)} {random.choice(APELLIDOS)}"
            v, _ = Vecino.objects.get_or_create(rut=f"{cuerpo}{digito_verificador(cuerpo)}", defaults={
                "nombre": nombre, "telefono": f"+56 9 {random.randint(1000, 9999)} {random.randint(1000, 9999)}",
                "correo": f"vecino{len(vecinos) + 1}@correo.test"})
            vecinos.append(v)

        operadores = [u for u in usuarios.values() if u.is_active and u.rol.alcance != "GLOBAL"]
        faltan = opciones["atenciones"] - Atencion.objects.count()
        nuevas = []
        for _ in range(max(0, faltan)):
            u = random.choice(operadores)
            s = random.choice(subs)
            nuevas.append(Atencion(
                vecino=random.choice(vecinos), tipo=s.tipo, subatencion=s, delegacion=u.delegaciones.first(),
                responsable=u, descripcion=f"Solicitud de ejemplo sobre {s.nombre.lower()}. Datos ficticios."))
        Atencion.objects.bulk_create(nuevas, batch_size=500)

        if not opciones["sin_transacciones"]:
            self._actividades(actual, usuarios, items, organizaciones, vecinos, hoy, opciones["actividades"])
            self._ausencias(actual, usuarios)
            self._tubo(delegaciones[0], usuarios, areas)

        self.stdout.write(self.style.SUCCESS(
            f"Datos de prueba listos: {Delegacion.objects.count()} delegaciones, {Rol.objects.count()} roles, "
            f"{Usuario.objects.count()} usuarios, {Item.objects.count()} ítems, {TipoAtencion.objects.count()} tipos, "
            f"{SubAtencion.objects.count()} sub atenciones, {Organizacion.objects.count()} organizaciones, "
            f"{Trimestre.objects.count()} trimestres, {Actividad.objects.count()} actividades, "
            f"{Compromiso.objects.count()} compromisos, {Vecino.objects.count()} vecinos, "
            f"{Atencion.objects.count()} atenciones."))
        self.stdout.write("Usuarios de prueba: " + ", ".join(u[0] for u in USUARIOS) + " (clave: SGR_CLAVE_DEMO).")

    def _actividades(self, trimestre, usuarios, items, organizaciones, vecinos, hoy, cantidad):
        if Actividad.objects.filter(trimestre=trimestre).exists():
            return
        dias = [trimestre.inicio + timedelta(days=i) for i in range((min(hoy, trimestre.fin) - trimestre.inicio).days + 1)]
        dias = [d for d in dias if d.weekday() < 5]
        if not dias:
            return
        funcionarios = [u for u in usuarios.values() if u.is_active and u.cargo]
        por_dia = {}
        for _ in range(cantidad):
            f = random.choice(funcionarios)
            metas = METAS.get(f.cargo, {})
            indices = [i for i in metas if not items[i].es_felicitacion]
            if not indices:
                continue
            fecha = random.choice(dias)
            if por_dia.get((f.pk, fecha), 0) >= MAX_ACTIVIDADES_DIA:
                continue
            por_dia[(f.pk, fecha)] = por_dia.get((f.pk, fecha), 0) + 1
            item = items[random.choice(indices)]
            vecino = random.choice(vecinos)
            azar = random.random()
            a = Actividad(
                trimestre=trimestre, funcionario=f, registrado_por=f, delegacion=f.delegaciones.first(), item=item,
                fecha=fecha, descripcion=f"Actividad de ejemplo: {item.nombre.lower()}. Datos ficticios.",
                tipo_registro="COORDINACION" if azar < 0.08 else "EJECUTADA",
                solicitante_tipo="ORGANIZACION" if item.ambito == "GES" and azar > 0.6 else "VECINO",
                nombre_contacto="" if 0.08 <= azar < 0.13 else vecino.nombre,
                telefono_contacto=vecino.telefono)
            if a.solicitante_tipo == "ORGANIZACION":
                opciones = [o for o in organizaciones if o.delegacion_id == a.delegacion_id]
                a.organizacion = random.choice(opciones) if opciones else None
                if a.organizacion is None:
                    a.solicitante_tipo = "VECINO"
            a.puntaje, a.motivo_sin_puntaje = calcular_puntaje(a)
            a.save()

    def _ausencias(self, trimestre, usuarios):
        if Ausencia.objects.filter(funcionario=usuarios["funcionario"]).exists():
            return
        desde = trimestre.inicio + timedelta(days=14)
        Ausencia.objects.create(funcionario=usuarios["funcionario"], tipo="VACACIONES", desde=desde,
                                hasta=desde + timedelta(days=4), registrado_por=usuarios["delegado"],
                                motivo="Feriado legal (dato de prueba)")
        Ausencia.objects.create(funcionario=usuarios["servicios"], tipo="LICENCIA", desde=desde + timedelta(days=7),
                                hasta=desde + timedelta(days=9), registrado_por=usuarios["delegado"])

    def _tubo(self, delegacion, usuarios, areas):
        if Compromiso.objects.exists():
            return
        responsables = [usuarios["funcionario"], usuarios["servicios"], usuarios["apoyo"], usuarios["delegado"]]
        orden = ["INGRESADO", "PENDIENTE", "EN_PROCESO", "REALIZADO"]
        for i, (titulo, solicitante, area, estado) in enumerate(COMPROMISOS):
            c = Compromiso.objects.create(titulo=titulo, solicitante=solicitante, area_apoyo=areas[area],
                                          delegacion=delegacion, responsable=responsables[i % len(responsables)],
                                          creado_por=usuarios["delegado"],
                                          descripcion=f"Compromiso de ejemplo: {titulo.lower()}. Datos ficticios.")
            HistorialCompromiso.objects.create(compromiso=c, estado_nuevo="INGRESADO", usuario=usuarios["delegado"],
                                               comentario="Compromiso ingresado al tubo.")
            for anterior, nuevo in zip(orden, orden[1:orden.index(estado) + 1]):
                if nuevo == "REALIZADO":
                    Evidencia.objects.create(compromiso=c, foto=foto_demo(c.codigo), descripcion="Trabajo terminado",
                                             estado="APROBADA", subida_por=c.responsable,
                                             revisada_por=usuarios["delegado"], revisada_en=timezone.now())
                    c.realizado_en = timezone.now()
                HistorialCompromiso.objects.create(compromiso=c, estado_anterior=anterior, estado_nuevo=nuevo,
                                                   usuario=c.responsable)
            c.estado = estado
            c.save()
        en_proceso = Compromiso.objects.filter(estado="EN_PROCESO").first()
        if en_proceso:
            Evidencia.objects.create(compromiso=en_proceso, foto=foto_demo(en_proceso.codigo),
                                     descripcion="Avance de la poda", subida_por=en_proceso.responsable, origen="APP")
