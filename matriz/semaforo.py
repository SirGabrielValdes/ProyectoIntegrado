"""
Cálculo automático del cumplimiento de metas (semáforo).

- Meta ajustada = meta × (días hábiles del trimestre − días hábiles de ausencia) ÷ días hábiles del trimestre.
- Cumplimiento de un ítem = puntos válidos ÷ meta ajustada, con tope de 120 %.
- Cumplimiento total = promedio de los ítems con meta.
- Semáforo: verde ≥ 100 %, amarillo 70 % a 99 %, rojo < 70 %.
"""
from collections import defaultdict
from datetime import timedelta

from django.db.models import Count, Sum

from catalogos.models import Delegacion
from cuentas.models import Usuario

from .models import Actividad, Ausencia, MetaTrimestre
from .reglas import TOPE_CUMPLIMIENTO, cumplimiento

UMBRAL_VERDE = 1.0
UMBRAL_AMARILLO = 0.7
SEMAFORO = {
    "VERDE": ("Verde", "Cumple la meta (≥ 100 %)"),
    "AMARILLO": ("Amarillo", "En riesgo (70 % a 99 %)"),
    "ROJO": ("Rojo", "Bajo la meta (< 70 %)"),
    "SIN_META": ("Sin meta", "Sin meta exigible en el trimestre"),
}


def color(valor):
    if valor is None:
        return "SIN_META"
    if valor >= UMBRAL_VERDE:
        return "VERDE"
    if valor >= UMBRAL_AMARILLO:
        return "AMARILLO"
    return "ROJO"


def dias_ausencia(funcionario, trimestre, ausencias=None):
    """Días hábiles de ausencia dentro del trimestre (sin contar dos veces días superpuestos)."""
    ausencias = ausencias if ausencias is not None else Ausencia.objects.filter(
        funcionario=funcionario, hasta__gte=trimestre.inicio, desde__lte=trimestre.fin)
    dias = set()
    for a in ausencias:
        dia = max(a.desde, trimestre.inicio)
        while dia <= min(a.hasta, trimestre.fin):
            if dia.weekday() < 5:
                dias.add(dia)
            dia += timedelta(days=1)
    return len(dias)


def _promedio(valores):
    valores = [v for v in valores if v is not None]
    return sum(valores) / len(valores) if valores else None


def resumen_funcionario(funcionario, trimestre, metas=None, puntos=None, ausencias=None):
    habiles = trimestre.dias_habiles or 1
    ausente = dias_ausencia(funcionario, trimestre, ausencias)
    factor = max(habiles - ausente, 0) / habiles
    if metas is None:
        metas = list(MetaTrimestre.objects.filter(trimestre=trimestre, cargo=funcionario.cargo).select_related("item"))
    if puntos is None:
        puntos = {r["item"]: r["p"] or 0 for r in Actividad.objects.filter(
            trimestre=trimestre, funcionario=funcionario).values("item").annotate(p=Sum("puntaje"))}
    items = []
    for m in metas:
        meta_aj = round(m.cantidad * factor, 1)
        pts = puntos.get(m.item_id, 0)
        cump = cumplimiento(pts, meta_aj)
        items.append({
            "item": m.item, "meta": m.cantidad, "meta_ajustada": meta_aj, "puntos": pts,
            "cumplimiento": cump, "color": color(cump),
            "sobre_tope": bool(meta_aj) and pts / meta_aj > TOPE_CUMPLIMIENTO,
            "puntos_sobre_tope": max(0, round(pts - meta_aj * TOPE_CUMPLIMIENTO, 1)) if meta_aj else 0,
        })
    total = _promedio(i["cumplimiento"] for i in items)
    return {"funcionario": funcionario, "items": items, "total": total, "color": color(total),
            "dias_habiles": habiles, "dias_ausencia": ausente, "factor": factor,
            "puntos": sum(puntos.values())}


def funcionarios_de(delegacion):
    return Usuario.objects.filter(delegaciones=delegacion, is_active=True).exclude(cargo="").order_by("nombre")


def resumen_delegacion(delegacion, trimestre):
    funcionarios = list(funcionarios_de(delegacion))
    metas_por_cargo = defaultdict(list)
    for m in MetaTrimestre.objects.filter(trimestre=trimestre).select_related("item"):
        metas_por_cargo[m.cargo].append(m)
    puntos = defaultdict(dict)
    for r in (Actividad.objects.filter(trimestre=trimestre, funcionario__in=funcionarios)
              .values("funcionario", "item").annotate(p=Sum("puntaje"))):
        puntos[r["funcionario"]][r["item"]] = r["p"] or 0
    ausencias = defaultdict(list)
    for a in Ausencia.objects.filter(funcionario__in=funcionarios, hasta__gte=trimestre.inicio,
                                     desde__lte=trimestre.fin):
        ausencias[a.funcionario_id].append(a)
    resumenes = [resumen_funcionario(f, trimestre, metas_por_cargo.get(f.cargo, []), puntos[f.pk],
                                     ausencias[f.pk]) for f in funcionarios]
    # Visión de equipo: por ítem se suman los puntos y las metas ajustadas de todos los funcionarios.
    por_item = {}
    for r in resumenes:
        for i in r["items"]:
            fila = por_item.setdefault(i["item"].pk, {"item": i["item"], "meta_ajustada": 0, "puntos": 0})
            fila["meta_ajustada"] += i["meta_ajustada"]
            fila["puntos"] += i["puntos"]
    items = []
    for fila in sorted(por_item.values(), key=lambda f: f["item"].codigo):
        fila["meta_ajustada"] = round(fila["meta_ajustada"], 1)
        fila["cumplimiento"] = cumplimiento(fila["puntos"], fila["meta_ajustada"])
        fila["color"] = color(fila["cumplimiento"])
        items.append(fila)
    total = _promedio(i["cumplimiento"] for i in items)
    registros = Actividad.objects.filter(trimestre=trimestre, delegacion=delegacion).aggregate(
        n=Count("id"), validas=Sum("puntaje"))
    return {"delegacion": delegacion, "funcionarios": resumenes, "items": items, "total": total,
            "color": color(total), "actividades": registros["n"] or 0, "validas": registros["validas"] or 0}


def resumen_general(trimestre, delegaciones=None):
    delegaciones = delegaciones if delegaciones is not None else Delegacion.objects.filter(activo=True)
    filas = [resumen_delegacion(d, trimestre) for d in delegaciones]
    total = _promedio(f["total"] for f in filas)
    conteo = defaultdict(int)
    for f in filas:
        conteo[f["color"]] += 1
    return {"delegaciones": filas, "total": total, "color": color(total), "conteo": dict(conteo)}
