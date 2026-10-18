from django.db import models

from core.validadores import validar_codigo


class Catalogo(models.Model):
    """Campos comunes de los mantenedores: código, nombre y estado."""

    codigo = models.CharField("Código", max_length=15, unique=True, validators=[validar_codigo])
    nombre = models.CharField("Nombre", max_length=100)
    activo = models.BooleanField("Estado", default=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} · {self.nombre}"

    def save(self, *args, **kwargs):
        # Códigos normalizados en mayúsculas: la unicidad no distingue mayúsculas.
        self.codigo = (self.codigo or "").strip().upper()
        super().save(*args, **kwargs)

    @property
    def estado_texto(self):
        return "Activo" if self.activo else "Inactivo"


class Delegacion(Catalogo):
    direccion = models.CharField("Dirección", max_length=150)
    comuna = models.CharField("Comuna", max_length=60, default="La Serena")

    class Meta(Catalogo.Meta):
        verbose_name = "delegación"
        verbose_name_plural = "delegaciones"

    @property
    def estado_texto(self):
        return "Activa" if self.activo else "Inactiva"


class Item(Catalogo):
    """Ítems y metas del proyecto."""

    descripcion = models.TextField("Descripción", max_length=500, blank=True)

    class Meta(Catalogo.Meta):
        verbose_name = "ítem"
        verbose_name_plural = "ítems y metas"


class TipoAtencion(Catalogo):
    descripcion = models.TextField("Descripción", max_length=500, blank=True)

    class Meta(Catalogo.Meta):
        verbose_name = "tipo de atención"
        verbose_name_plural = "tipos de atención"


class SubAtencion(Catalogo):
    tipo = models.ForeignKey(
        TipoAtencion, on_delete=models.PROTECT, related_name="subatenciones",
        verbose_name="Tipo de Atención",
    )

    class Meta(Catalogo.Meta):
        verbose_name = "sub atención"
        verbose_name_plural = "sub atenciones"
        constraints = [models.UniqueConstraint(fields=["tipo", "nombre"], name="subatencion_nombre_por_tipo")]
