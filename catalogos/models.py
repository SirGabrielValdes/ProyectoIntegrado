from django.db import models

from core.codigos import CodigoAutomatico

COMUNA_POR_DEFECTO = "La Serena"


class Catalogo(CodigoAutomatico):
    """Campos comunes de los mantenedores: código automático, nombre y estado."""

    codigo = models.CharField("Código", max_length=15, unique=True, blank=True, editable=False)
    nombre = models.CharField("Nombre", max_length=100)
    activo = models.BooleanField("Estado", default=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} · {self.nombre}"

    @property
    def estado_texto(self):
        return "Activo" if self.activo else "Inactivo"


class Delegacion(Catalogo):
    PREFIJO = "DEL"
    direccion = models.CharField("Dirección", max_length=150)
    comuna = models.CharField("Comuna", max_length=60, default=COMUNA_POR_DEFECTO)

    class Meta(Catalogo.Meta):
        verbose_name = "delegación"
        verbose_name_plural = "delegaciones"

    @property
    def estado_texto(self):
        return "Activa" if self.activo else "Inactiva"


class Item(Catalogo):
    """Ítems de la matriz SGR: cada actividad válida suma 1 punto en su ítem."""

    PREFIJO = "ITM"
    AMBITOS = [("GES", "Gestión"), ("SOC", "Social")]
    descripcion = models.TextField("Descripción", max_length=500, blank=True)
    ambito = models.CharField("Ámbito", max_length=3, choices=AMBITOS, default="GES",
                              help_text="Define el prefijo del código de sus actividades (GES o SOC).")
    es_felicitacion = models.BooleanField(
        "Ítem de felicitaciones", default=False,
        help_text="Solo el delegado puede registrar actividades en este ítem, con respaldo formal.")

    class Meta(Catalogo.Meta):
        verbose_name = "ítem"
        verbose_name_plural = "ítems y metas"


class TipoAtencion(Catalogo):
    PREFIJO = "TAT"
    descripcion = models.TextField("Descripción", max_length=500, blank=True)

    class Meta(Catalogo.Meta):
        verbose_name = "tipo de atención"
        verbose_name_plural = "tipos de atención"


class SubAtencion(Catalogo):
    PREFIJO = "SAT"
    tipo = models.ForeignKey(
        TipoAtencion, on_delete=models.PROTECT, related_name="subatenciones",
        verbose_name="Tipo de Atención",
    )

    class Meta(Catalogo.Meta):
        verbose_name = "sub atención"
        verbose_name_plural = "sub atenciones"
        constraints = [models.UniqueConstraint(fields=["tipo", "nombre"], name="subatencion_nombre_por_tipo")]
