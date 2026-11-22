"""Reglas del tubo de trabajo, compartidas por la web y la API móvil."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from PIL import Image, UnidentifiedImageError

from .models import Compromiso, Evidencia, HistorialCompromiso

FORMATOS_FOTO = {"JPEG", "PNG", "WEBP"}
MAX_FOTO = 8 * 1024 * 1024


def validar_foto(archivo):
    if not archivo:
        raise ValidationError("Adjunte una fotografía.")
    if archivo.size > MAX_FOTO:
        raise ValidationError("La fotografía no puede superar 8 MB.")
    try:
        imagen = Image.open(archivo)
        formato = imagen.format
        imagen.verify()
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise ValidationError("El archivo no es una imagen válida.")
    finally:
        archivo.seek(0)
    if formato not in FORMATOS_FOTO:
        raise ValidationError("La fotografía debe ser JPG, PNG o WEBP.")


@transaction.atomic
def avanzar(compromiso, usuario, comentario="", destino=None):
    """
    Mueve el compromiso al siguiente estado del tubo y deja registro en el historial.
    `destino` (al arrastrar en el tablero) debe ser exactamente la etapa siguiente.
    """
    compromiso = Compromiso.objects.select_for_update().get(pk=compromiso.pk)
    siguiente = compromiso.siguiente
    if not siguiente:
        raise ValidationError("El compromiso ya está realizado.")
    nuevo = siguiente[0]
    if destino and destino != nuevo:
        nombres = dict(Compromiso.ESTADOS)
        raise ValidationError(f"{compromiso.codigo} solo puede pasar de «{nombres[compromiso.estado]}» a "
                              f"«{nombres[nuevo]}»: las etapas avanzan de una en una.")
    if nuevo == "REALIZADO" and not compromiso.tiene_evidencia_aprobada():
        raise ValidationError("Para marcarlo como realizado debe tener al menos una evidencia fotográfica aprobada.")
    anterior = compromiso.estado
    compromiso.estado = nuevo
    if nuevo == "REALIZADO":
        compromiso.realizado_en = timezone.now()
    compromiso.save(update_fields=["estado", "realizado_en", "actualizado"])
    HistorialCompromiso.objects.create(compromiso=compromiso, estado_anterior=anterior, estado_nuevo=nuevo,
                                       usuario=usuario, comentario=comentario[:300])
    return compromiso


def registrar_ingreso(compromiso, usuario):
    HistorialCompromiso.objects.create(compromiso=compromiso, estado_nuevo=compromiso.estado, usuario=usuario,
                                       comentario="Compromiso ingresado al tubo.")


def subir_evidencia(compromiso, usuario, foto, descripcion="", origen="WEB"):
    if compromiso.estado == "REALIZADO":
        raise ValidationError("El compromiso ya está realizado: no admite nuevas evidencias.")
    validar_foto(foto)
    return Evidencia.objects.create(compromiso=compromiso, foto=foto, descripcion=descripcion[:200],
                                    origen=origen, subida_por=usuario)


def revisar_evidencia(evidencia, usuario, aprobar, comentario=""):
    if evidencia.estado != "PENDIENTE":
        raise ValidationError("Esta evidencia ya fue revisada.")
    if not aprobar and not comentario.strip():
        raise ValidationError("Indique el motivo del rechazo.")
    evidencia.estado = "APROBADA" if aprobar else "RECHAZADA"
    evidencia.revisada_por = usuario
    evidencia.revisada_en = timezone.now()
    evidencia.comentario_revision = comentario.strip()[:300]
    evidencia.save(update_fields=["estado", "revisada_por", "revisada_en", "comentario_revision"])
    return evidencia
