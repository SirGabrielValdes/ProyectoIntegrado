"""
Códigos automáticos con prefijo y correlativo (por ejemplo DEL-00008, TUB-00060).

El código lo asigna el sistema al guardar por primera vez; el usuario nunca lo
ingresa ni lo edita. Si dos registros se guardan al mismo tiempo y chocan en el
correlativo, la restricción única de la base lo detecta y se reintenta.
"""
from django.db import IntegrityError, models, transaction

ANCHO = 5


def siguiente_codigo(modelo, prefijo, campo="codigo"):
    inicio = f"{prefijo}-"
    existentes = modelo._default_manager.filter(**{f"{campo}__startswith": inicio}).values_list(campo, flat=True)
    numeros = [int(c[len(inicio):]) for c in existentes if c[len(inicio):].isdigit()]
    return f"{inicio}{max(numeros, default=0) + 1:0{ANCHO}d}"


class CodigoAutomatico(models.Model):
    """Mezcla para modelos con campo `codigo` generado automáticamente."""

    PREFIJO = ""
    REINTENTOS = 5

    class Meta:
        abstract = True

    def prefijo_codigo(self):
        return self.PREFIJO

    def save(self, *args, **kwargs):
        if self.codigo:
            return super().save(*args, **kwargs)
        for intento in range(self.REINTENTOS):
            self.codigo = siguiente_codigo(type(self), self.prefijo_codigo())
            try:
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except IntegrityError:
                self.codigo = ""
                if intento == self.REINTENTOS - 1:
                    raise
