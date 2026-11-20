"""
Matriz SGR: trimestres de evaluación, metas, organizaciones comunitarias,
actividades con puntaje y ausencias que ajustan las metas del semáforo.
"""
from datetime import timedelta

from django.conf import settings
from django.db import models

from catalogos.models import COMUNA_POR_DEFECTO, Catalogo, Delegacion, Item
from core.codigos import CodigoAutomatico
from cuentas.models import CARGOS


def dias_habiles(desde, hasta):
    """Días de lunes a viernes entre dos fechas, ambas incluidas."""
    if not desde or not hasta or hasta < desde:
        return 0
    total, dia = 0, desde
    while dia <= hasta:
        if dia.weekday() < 5:
            total += 1
        dia += timedelta(days=1)
    return total


class Trimestre(CodigoAutomatico):
    PREFIJO = "TRI"
    ESTADOS = [("PLANIFICADO", "Planificado"), ("ABIERTO", "Abierto"), ("CERRADO", "Cerrado")]

    codigo = models.CharField("Código", max_length=15, unique=True, blank=True, editable=False)
    nombre = models.CharField("Nombre", max_length=60)
    inicio = models.DateField("Fecha de inicio")
    fin = models.DateField("Fecha de término")
    estado = models.CharField("Estado", max_length=12, choices=ESTADOS, default="PLANIFICADO")
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-inicio"]
        verbose_name = "trimestre"

    def __str__(self):
        return f"{self.codigo} · {self.nombre}"

    @classmethod
    def abierto(cls):
        return cls.objects.filter(estado="ABIERTO").first()

    @property
    def estado_texto(self):
        return self.get_estado_display()

    @property
    def dias_habiles(self):
        return dias_habiles(self.inicio, self.fin)

    def contiene(self, fecha):
        return self.inicio <= fecha <= self.fin


class MetaTrimestre(models.Model):
    """Cantidad de actividades válidas esperadas por ítem para un cargo en el trimestre."""

    trimestre = models.ForeignKey(Trimestre, on_delete=models.CASCADE, related_name="metas")
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="metas", verbose_name="Ítem")
    cargo = models.CharField("Cargo", max_length=30, choices=CARGOS)
    cantidad = models.PositiveIntegerField("Meta (actividades)")

    class Meta:
        ordering = ["item__codigo", "cargo"]
        verbose_name = "meta"
        constraints = [models.UniqueConstraint(fields=["trimestre", "item", "cargo"], name="meta_unica")]

    def __str__(self):
        return f"{self.item.nombre} · {self.get_cargo_display()}: {self.cantidad}"


class Organizacion(Catalogo):
    """Juntas de vecinos y organizaciones comunitarias funcionales (leyes 19.418 y 20.500)."""

    PREFIJO = "ORG"
    TIPOS = [
        ("JJVV", "Junta de Vecinos"),
        ("ADULTO_MAYOR", "Club de Adulto Mayor"),
        ("DEPORTIVA", "Organización Deportiva"),
        ("CULTURAL", "Centro de Madres / Centro Cultural / Agrupación Juvenil"),
        ("COMITE", "Comité de Vecinos, de allegados o de seguridad"),
        ("OTRA", "Otra organización funcional"),
    ]

    tipo = models.CharField("Tipo", max_length=20, choices=TIPOS)
    subtipo = models.CharField("Subtipo", max_length=80, blank=True,
                               help_text="Opcional, por ejemplo «Comité de agua potable rural».")
    delegacion = models.ForeignKey(Delegacion, on_delete=models.PROTECT, related_name="organizaciones",
                                   verbose_name="Delegación")
    direccion = models.CharField("Dirección", max_length=150, blank=True)
    comuna = models.CharField("Comuna", max_length=60, default=COMUNA_POR_DEFECTO)
    dirigente = models.CharField("Dirigente o contacto", max_length=100, blank=True)
    telefono = models.CharField("Teléfono", max_length=20, blank=True)

    class Meta(Catalogo.Meta):
        verbose_name = "organización"
        verbose_name_plural = "organizaciones"

    @property
    def estado_texto(self):
        return "Activa" if self.activo else "Inactiva"


class Actividad(CodigoAutomatico):
    """Registro de la matriz SGR. Cada actividad válida suma 1 punto en su ítem."""

    TIPOS_REGISTRO = [
        ("EJECUTADA", "Acción ejecutada"),
        ("COORDINACION", "Coordinación previa (correos, llamadas, invitaciones)"),
    ]
    SOLICITANTES = [
        ("VECINO", "Vecino"),
        ("ORGANIZACION", "Organización comunitaria"),
        ("DELEGADO", "El propio delegado"),
    ]

    codigo = models.CharField("Código", max_length=15, unique=True, blank=True, editable=False)
    trimestre = models.ForeignKey(Trimestre, on_delete=models.PROTECT, related_name="actividades")
    funcionario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                    related_name="actividades", verbose_name="Funcionario")
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                       related_name="actividades_registradas", verbose_name="Registrado por")
    delegacion = models.ForeignKey(Delegacion, on_delete=models.PROTECT, related_name="actividades",
                                   verbose_name="Delegación")
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="actividades", verbose_name="Ítem")
    fecha = models.DateField("Fecha de la actividad")
    tipo_registro = models.CharField("Tipo de registro", max_length=15, choices=TIPOS_REGISTRO, default="EJECUTADA")
    solicitante_tipo = models.CharField("Solicitante", max_length=15, choices=SOLICITANTES, default="VECINO")
    organizacion = models.ForeignKey(Organizacion, on_delete=models.PROTECT, null=True, blank=True,
                                     related_name="actividades", verbose_name="Organización")
    nombre_contacto = models.CharField("Nombre del vecino o usuario", max_length=100, blank=True)
    telefono_contacto = models.CharField("Teléfono del vecino o usuario", max_length=20, blank=True)
    descripcion = models.TextField("Descripción de la actividad", max_length=1000)
    respaldo = models.FileField("Respaldo formal", upload_to="respaldos/%Y/%m", blank=True)
    puntaje = models.PositiveSmallIntegerField("Puntaje", default=0)
    motivo_sin_puntaje = models.CharField("Motivo sin puntaje", max_length=200, blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-creado"]
        verbose_name = "actividad"
        verbose_name_plural = "actividades"
        indexes = [models.Index(fields=["funcionario", "fecha"]), models.Index(fields=["trimestre", "item"])]

    def __str__(self):
        return f"{self.codigo} · {self.item.nombre}"

    def prefijo_codigo(self):
        return self.item.ambito if self.item_id else "GES"

    @property
    def puntaje_texto(self):
        return f"{self.puntaje} punto" if self.puntaje == 1 else f"{self.puntaje} puntos"


class Ausencia(models.Model):
    """Días libres, vacaciones, días administrativos y licencias: ajustan la meta del funcionario."""

    TIPOS = [
        ("DIA_LIBRE", "Día libre"),
        ("VACACIONES", "Vacaciones"),
        ("ADMINISTRATIVO", "Día administrativo"),
        ("LICENCIA", "Licencia médica"),
    ]

    funcionario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                    related_name="ausencias", verbose_name="Funcionario")
    tipo = models.CharField("Tipo", max_length=15, choices=TIPOS)
    desde = models.DateField("Desde")
    hasta = models.DateField("Hasta")
    motivo = models.CharField("Observación", max_length=200, blank=True)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                       related_name="ausencias_registradas", verbose_name="Registrado por")
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-desde"]
        verbose_name = "ausencia"

    def __str__(self):
        return f"{self.get_tipo_display()} · {self.funcionario} ({self.desde:%d-%m-%Y} a {self.hasta:%d-%m-%Y})"

    def dias_habiles_en(self, inicio, fin):
        return dias_habiles(max(self.desde, inicio), min(self.hasta, fin))

    @property
    def dias(self):
        return dias_habiles(self.desde, self.hasta)
