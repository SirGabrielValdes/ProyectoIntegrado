import re

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

validar_codigo = RegexValidator(
    r"^[A-Z0-9][A-Z0-9-]{1,14}$",
    "Use de 2 a 15 caracteres: letras mayúsculas, números o guion (ej.: DEL01).",
)

validar_texto = RegexValidator(
    r"^[\wÁÉÍÓÚÜÑáéíóúüñ0-9 .,;:()'/#°º&-]+$",
    "Contiene caracteres no permitidos.",
)


def normalizar_rut(valor):
    return re.sub(r"[^0-9kK]", "", valor or "").upper()


def formatear_rut(valor):
    rut = normalizar_rut(valor)
    if len(rut) < 2:
        return valor
    cuerpo, dv = rut[:-1], rut[-1]
    cuerpo_fmt = f"{int(cuerpo):,}".replace(",", ".")
    return f"{cuerpo_fmt}-{dv}"


def digito_verificador(cuerpo):
    suma, factor = 0, 2
    for d in reversed(str(cuerpo)):
        suma += int(d) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - (suma % 11)
    return {11: "0", 10: "K"}.get(resto, str(resto))


def validar_rut(valor):
    rut = normalizar_rut(valor)
    if len(rut) < 8 or len(rut) > 9 or not rut[:-1].isdigit():
        raise ValidationError("RUT inválido. Use el formato 12.345.678-9.")
    if digito_verificador(rut[:-1]) != rut[-1]:
        raise ValidationError("El dígito verificador del RUT no es correcto.")
