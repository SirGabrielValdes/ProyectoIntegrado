"""
Reglas de negocio de la matriz SGR (correo «Matriz SGR 4to semestre; puntos a considerar»).

1. Si el solicitante es el propio delegado, la actividad es «otra gestión»: no suma puntaje.
2. Sin nombre y teléfono del vecino o usuario no hay puntaje.
3. Máximo 7 actividades por funcionario y día (cuentan todas, también las coordinaciones).
4. La semana (lunes a viernes) se cierra el lunes siguiente: desde el martes no se ingresan actividades de esa semana.
5. Las coordinaciones previas (correos, llamadas, invitaciones) no dan punto; solo la acción ejecutada.
7. Cada ítem tiene un tope de 120 % de cumplimiento (ver semaforo.py).
8. Las felicitaciones solo las registra el delegado, con respaldo formal.
9. Las ausencias las ingresa el delegado y ajustan las metas (ver semaforo.py).
"""
from datetime import timedelta

MAX_ACTIVIDADES_DIA = 7
TOPE_CUMPLIMIENTO = 1.2


def lunes_de(fecha):
    return fecha - timedelta(days=fecha.weekday())


def limite_ingreso(fecha):
    """Último día en que se puede ingresar una actividad con esta fecha: el lunes siguiente."""
    return lunes_de(fecha) + timedelta(days=7)


def errores_de_fecha(fecha, hoy):
    """Valida día hábil, fecha no futura y semana no cerrada."""
    errores = []
    if fecha > hoy:
        errores.append("No se pueden registrar actividades con fecha futura.")
    if fecha.weekday() > 4:
        errores.append("Solo se registran actividades de lunes a viernes.")
    if hoy > limite_ingreso(fecha):
        errores.append(f"La semana del {lunes_de(fecha):%d-%m-%Y} está cerrada: el plazo para ingresarla venció "
                       f"el lunes {limite_ingreso(fecha):%d-%m-%Y}.")
    return errores


def calcular_puntaje(actividad):
    """Devuelve (puntaje, motivo). Cada actividad válida suma 1 punto."""
    if actividad.tipo_registro == "COORDINACION":
        return 0, "Coordinación previa: solo suma la acción ejecutada."
    if actividad.solicitante_tipo == "DELEGADO":
        return 0, "El usuario es el propio delegado: se registra como otra gestión."
    if not (actividad.nombre_contacto or "").strip() or not (actividad.telefono_contacto or "").strip():
        return 0, "Falta el nombre o el teléfono del vecino o usuario."
    return 1, ""


def cumplimiento(puntos, meta):
    """Cumplimiento de un ítem con tope de 120 %. Sin meta no hay cumplimiento exigible."""
    if not meta or meta <= 0:
        return None
    return min(puntos / meta, TOPE_CUMPLIMIENTO)
