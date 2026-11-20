"""
Tubo de trabajo: compromisos derivados para seguimiento, con estados, historial
y evidencias fotográficas que el delegado aprueba o rechaza.
"""
import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from catalogos.models import Catalogo, Delegacion
from core.codigos import CodigoAutomatico


class AreaApoyo(Catalogo):
    """Dirección o departamento municipal que apoya la ejecución (Obras, Tránsito, etc.)."""

    PREFIJO = "ARE"
    descripcion = models.CharField("Descripción", max_length=200, blank=True)

    class Meta(Catalogo.Meta):
        verbose_name = "área de apoyo"
        verbose_name_plural = "áreas de apoyo"

    @property
    def estado_texto(self):
        return "Activa" if self.activo else "Inactiva"


class Compromiso(CodigoAutomatico):
    PREFIJO = "TUB"
    ESTADOS = [
        ("INGRESADO", "Ingresado"),
        ("PENDIENTE", "Pendiente"),
        ("EN_PROCESO", "En proceso"),
        ("REALIZADO", "Realizado"),
    ]
    # Avance permitido: estado actual -> (siguiente estado, texto del botón)
    SIGUIENTE = {
        "INGRESADO": ("PENDIENTE", "A Pendiente"),
        "PENDIENTE": ("EN_PROCESO", "A Proceso"),
        "EN_PROCESO": ("REALIZADO", "Realizar"),
    }

    codigo = models.CharField("Código", max_length=15, unique=True, blank=True, editable=False)
    titulo = models.CharField("Compromiso", max_length=150)
    descripcion = models.TextField("Detalle", max_length=1500, blank=True)
    solicitante = models.CharField("Solicitante", max_length=120)
    actividad = models.ForeignKey("matriz.Actividad", on_delete=models.PROTECT, null=True, blank=True,
                                  related_name="compromisos", verbose_name="Actividad de origen")
    atencion = models.ForeignKey("atenciones.Atencion", on_delete=models.PROTECT, null=True, blank=True,
                                 related_name="compromisos", verbose_name="Atención de origen")
    delegacion = models.ForeignKey(Delegacion, on_delete=models.PROTECT, related_name="compromisos",
                                   verbose_name="Delegación")
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                    related_name="compromisos", verbose_name="Responsable")
    area_apoyo = models.ForeignKey(AreaApoyo, on_delete=models.PROTECT, null=True, blank=True,
                                   related_name="compromisos", verbose_name="Área de apoyo")
    estado = models.CharField("Estado", max_length=12, choices=ESTADOS, default="INGRESADO")
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                   related_name="compromisos_creados", verbose_name="Ingresado por")
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
    realizado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-creado"]
        verbose_name = "compromiso"

    def __str__(self):
        return f"{self.codigo} · {self.titulo}"

    @property
    def referencia(self):
        """Código de la gestión o caso de origen (GES/SOC de la actividad, o folio de la atención)."""
        if self.actividad_id:
            return self.actividad.codigo
        if self.atencion_id:
            return self.atencion.folio
        return ""

    @property
    def estado_texto(self):
        return self.get_estado_display()

    @property
    def siguiente(self):
        return self.SIGUIENTE.get(self.estado)

    def tiene_evidencia_aprobada(self):
        return self.evidencias.filter(estado="APROBADA").exists()


class HistorialCompromiso(models.Model):
    compromiso = models.ForeignKey(Compromiso, on_delete=models.CASCADE, related_name="historial")
    estado_anterior = models.CharField(max_length=12, choices=Compromiso.ESTADOS, blank=True)
    estado_nuevo = models.CharField(max_length=12, choices=Compromiso.ESTADOS)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    comentario = models.CharField(max_length=300, blank=True)
    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-fecha", "-pk"]


class Evidencia(models.Model):
    ESTADOS = [("PENDIENTE", "Pendiente de revisión"), ("APROBADA", "Aprobada"), ("RECHAZADA", "Rechazada")]
    ORIGENES = [("WEB", "Sitio web"), ("APP", "App móvil")]

    compromiso = models.ForeignKey(Compromiso, on_delete=models.CASCADE, related_name="evidencias")
    foto = models.ImageField("Fotografía", upload_to="evidencias/%Y/%m")
    descripcion = models.CharField("Descripción", max_length=200, blank=True)
    origen = models.CharField(max_length=3, choices=ORIGENES, default="WEB")
    estado = models.CharField(max_length=10, choices=ESTADOS, default="PENDIENTE")
    subida_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                   related_name="evidencias_subidas")
    subida_en = models.DateTimeField(auto_now_add=True)
    revisada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
                                     related_name="evidencias_revisadas")
    revisada_en = models.DateTimeField(null=True, blank=True)
    comentario_revision = models.CharField("Comentario de revisión", max_length=300, blank=True)

    class Meta:
        ordering = ["-subida_en"]
        verbose_name = "evidencia"


class TokenApi(models.Model):
    """
    Token de acceso de la app móvil (cabecera «Authorization: Token <clave>»).
    Solo se guarda el hash SHA-256: la clave se muestra una única vez al emitirla.
    """

    VIGENCIA_DIAS = 30

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tokens_api")
    clave_hash = models.CharField(max_length=64, unique=True, editable=False)
    creado = models.DateTimeField(auto_now_add=True)
    expira = models.DateTimeField()
    ultimo_uso = models.DateTimeField(null=True, blank=True)

    @staticmethod
    def resumir(clave):
        return hashlib.sha256(clave.encode()).hexdigest()

    @classmethod
    def emitir(cls, usuario):
        clave = secrets.token_urlsafe(32)
        token = cls.objects.create(usuario=usuario, clave_hash=cls.resumir(clave),
                                   expira=timezone.now() + timedelta(days=cls.VIGENCIA_DIAS))
        return token, clave

    @classmethod
    def validar(cls, clave):
        token = cls.objects.select_related("usuario", "usuario__rol").filter(
            clave_hash=cls.resumir(clave or ""), expira__gt=timezone.now()).first()
        if token:
            cls.objects.filter(pk=token.pk).update(ultimo_uso=timezone.now())
        return token
