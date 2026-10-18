from datetime import date, datetime

from django import forms, template
from django.utils import timezone
from django.utils.html import format_html

register = template.Library()


@register.filter
def valor(dato):
    """Presentación homogénea de valores en tablas y fichas."""
    if dato is None or dato == "":
        return "—"
    if isinstance(dato, bool):
        return "Sí" if dato else "No"
    if isinstance(dato, datetime):
        return timezone.localtime(dato).strftime("%d-%m-%Y %H:%M")
    if isinstance(dato, date):
        return dato.strftime("%d-%m-%Y")
    return dato


@register.filter
def tipo_widget(campo):
    w = campo.field.widget
    if isinstance(w, forms.CheckboxSelectMultiple):
        return "checks"
    if isinstance(w, forms.CheckboxInput):
        return "check"
    if isinstance(w, forms.RadioSelect):
        return "radio"
    if isinstance(w, forms.PasswordInput):
        return "clave"
    if isinstance(w, forms.HiddenInput):
        return "oculto"
    if isinstance(w, forms.Textarea):
        return "area"
    return "normal"


@register.simple_tag
def icono(nombre, clase=""):
    return format_html('<svg class="icono {}" aria-hidden="true" focusable="false"><use href="#i-{}"></use></svg>',
                       clase, nombre)


@register.simple_tag
def estado(texto):
    activo = texto in ("Activo", "Activa")
    clase = "estado-activo" if activo else "estado-inactivo"
    simbolo = "check" if activo else "pausa"
    return format_html('<span class="estado {}"><svg class="icono icono-sm" aria-hidden="true"><use href="#i-{}"></use>'
                       '</svg>{}</span>', clase, simbolo, texto)


@register.simple_tag(takes_context=True)
def url_pagina(context, numero):
    parametros = context.get("parametros", "")
    return f"?{parametros}&pagina={numero}" if parametros else f"?pagina={numero}"
