import re

from django.core.exceptions import ValidationError

REQUISITOS_CLAVE = [
    ("largo", "Entre 8 y 64 caracteres"),
    ("mayuscula", "Al menos una letra mayúscula"),
    ("minuscula", "Al menos una letra minúscula"),
    ("numero", "Al menos un número"),
    ("especial", "Al menos un carácter especial (ej.: ! @ # $ % * ?)"),
]


def requisitos_incumplidos(clave):
    clave = clave or ""
    pruebas = {
        "largo": 8 <= len(clave) <= 64,
        "mayuscula": re.search(r"[A-ZÁÉÍÓÚÑ]", clave) is not None,
        "minuscula": re.search(r"[a-záéíóúñ]", clave) is not None,
        "numero": re.search(r"\d", clave) is not None,
        "especial": re.search(r"[^\w\s]|_", clave) is not None,
    }
    return [texto for clave_req, texto in REQUISITOS_CLAVE if not pruebas[clave_req]]


class PoliticaClaveValidator:
    """Política de contraseñas del SGR (se muestra también en la interfaz)."""

    def validate(self, password, user=None):
        faltan = requisitos_incumplidos(password)
        if faltan:
            raise ValidationError(
                ["La contraseña no cumple: " + "; ".join(f.lower() for f in faltan) + "."],
                code="politica_clave",
            )

    def get_help_text(self):
        return "; ".join(t for _, t in REQUISITOS_CLAVE)
