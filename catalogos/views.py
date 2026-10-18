from django import forms

from core.crud import Columna, Filtro, FormularioBase, Mantenedor, filtro_estado

from .models import Delegacion, Item, SubAtencion, TipoAtencion


# --- Delegaciones ------------------------------------------------------------
class DelegacionForm(FormularioBase):
    class Meta:
        model = Delegacion
        fields = ["codigo", "nombre", "direccion", "comuna", "activo"]
        labels = {"activo": "Activa"}

    def clean(self):
        datos = super().clean()
        if self.instance.pk and self.instance.activo and not datos.get("activo"):
            if self.request and self.request.delegacion_activa == self.instance:
                self.add_error("activo", "No puede desactivar su delegación activa. Cambie de contexto primero.")
        return datos


class DelegacionesMantenedor(Mantenedor):
    modulo = "delegaciones"
    model = Delegacion
    form_class = DelegacionForm
    titulo = "Delegaciones municipales"
    singular = "delegación"
    femenino = True
    campos_busqueda = ["codigo", "nombre", "direccion", "comuna"]
    columnas = [
        Columna("Código", "codigo", "enlace"),
        Columna("Nombre", "nombre"),
        Columna("Dirección", "direccion"),
        Columna("Comuna", "comuna"),
        Columna("Estado", "estado_texto", "estado"),
    ]
    columnas_excel = [("Código", "codigo"), ("Nombre", "nombre"), ("Dirección", "direccion"),
                      ("Comuna", "comuna"), ("Estado", "estado_texto"),
                      ("Usuarios asignados", lambda d: d.usuarios.count())]
    detalle = [("Código", "codigo"), ("Nombre", "nombre"), ("Dirección", "direccion"),
               ("Comuna", "comuna"), ("Usuarios asignados", lambda d: d.usuarios.count()),
               ("Atenciones registradas", lambda d: d.atenciones.count())]
    filtros = [filtro_estado(femenino=True)]
    placeholder_busqueda = "Buscar por código, nombre, dirección o comuna…"

    def queryset(self, request):
        if request.user.rol.es_global:
            return Delegacion.objects.all()
        return request.user.delegaciones.all()

    def motivo_no_eliminar(self, request, obj):
        usuarios, atenciones = obj.usuarios.count(), obj.atenciones.count()
        if usuarios or atenciones:
            return (f"No se puede eliminar «{obj}»: tiene {usuarios} usuario(s) y {atenciones} atención(es) "
                    "asociados. Puede desactivarla en su lugar.")
        if request.delegacion_activa == obj:
            return "No puede eliminar su delegación activa."
        return None

    def motivo_no_cambiar_estado(self, request, obj):
        if obj.activo and request.delegacion_activa == obj:
            return "No puede desactivar su delegación activa. Cambie de contexto primero."
        return None


# --- Ítems y metas -----------------------------------------------------------
class ItemForm(FormularioBase):
    class Meta:
        model = Item
        fields = ["codigo", "nombre", "descripcion", "activo"]
        widgets = {"descripcion": forms.Textarea}
        labels = {"activo": "Activo"}


class ItemsMantenedor(Mantenedor):
    modulo = "items"
    model = Item
    form_class = ItemForm
    titulo = "Ítems y metas"
    singular = "ítem"
    campos_busqueda = ["codigo", "nombre", "descripcion"]
    columnas = [
        Columna("Código", "codigo", "enlace"),
        Columna("Nombre", "nombre"),
        Columna("Descripción", lambda i: (i.descripcion[:70] + "…") if len(i.descripcion) > 70 else i.descripcion),
        Columna("Estado", "estado_texto", "estado"),
    ]
    columnas_excel = [("Código", "codigo"), ("Nombre", "nombre"), ("Descripción", "descripcion"),
                      ("Estado", "estado_texto")]
    detalle = [("Código", "codigo"), ("Nombre", "nombre"), ("Descripción", "descripcion")]
    filtros = [filtro_estado()]
    placeholder_busqueda = "Buscar por código, nombre o descripción…"


# --- Tipo de Atención --------------------------------------------------------
class TipoAtencionForm(FormularioBase):
    class Meta:
        model = TipoAtencion
        fields = ["codigo", "nombre", "descripcion", "activo"]
        widgets = {"descripcion": forms.Textarea}
        labels = {"activo": "Activo"}

    unicos = {"codigo": "Ya existe un registro con este código.",
              "nombre": "Ya existe un tipo de atención con este nombre."}

    def clean(self):
        datos = super().clean()
        if self.instance.pk and self.instance.activo and not datos.get("activo"):
            activas = self.instance.subatenciones.filter(activo=True).count()
            if activas:
                self.add_error("activo", f"Tiene {activas} sub atención(es) activa(s). Desactívelas primero.")
        return datos


class TiposMantenedor(Mantenedor):
    modulo = "tipos"
    model = TipoAtencion
    form_class = TipoAtencionForm
    titulo = "Tipos de Atención"
    singular = "tipo de atención"
    campos_busqueda = ["codigo", "nombre", "descripcion"]
    columnas = [
        Columna("Código", "codigo", "enlace"),
        Columna("Nombre", "nombre"),
        Columna("Descripción", lambda t: (t.descripcion[:60] + "…") if len(t.descripcion) > 60 else t.descripcion),
        Columna("Sub atenciones", lambda t: t.subatenciones.count()),
        Columna("Estado", "estado_texto", "estado"),
    ]
    columnas_excel = [("Código", "codigo"), ("Nombre", "nombre"), ("Descripción", "descripcion"),
                      ("Sub atenciones", lambda t: t.subatenciones.count()), ("Estado", "estado_texto")]
    detalle = [("Código", "codigo"), ("Nombre", "nombre"), ("Descripción", "descripcion"),
               ("Sub atenciones", lambda t: ", ".join(s.nombre for s in t.subatenciones.all()) or "—"),
               ("Atenciones registradas", lambda t: t.atenciones.count())]
    filtros = [filtro_estado()]
    placeholder_busqueda = "Buscar por código, nombre o descripción…"

    def motivo_no_eliminar(self, request, obj):
        subs, atenciones = obj.subatenciones.count(), obj.atenciones.count()
        if subs or atenciones:
            return (f"No se puede eliminar «{obj}»: tiene {subs} sub atención(es) y {atenciones} atención(es) "
                    "relacionadas. Puede desactivarlo en su lugar.")
        return None

    def motivo_no_cambiar_estado(self, request, obj):
        activas = obj.subatenciones.filter(activo=True).count()
        if obj.activo and activas:
            return f"No se puede desactivar «{obj}»: tiene {activas} sub atención(es) activa(s). Desactívelas primero."
        return None


# --- Sub Atención ------------------------------------------------------------
class SubAtencionForm(FormularioBase):
    class Meta:
        model = SubAtencion
        fields = ["codigo", "nombre", "tipo", "activo"]
        labels = {"activo": "Activa"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = TipoAtencion.objects.filter(activo=True)
        if self.instance.pk:
            qs = qs | TipoAtencion.objects.filter(pk=self.instance.tipo_id)
        self.fields["tipo"].queryset = qs.distinct()
        self.fields["tipo"].empty_label = "Seleccione un tipo…"

    def clean(self):
        datos = super().clean()
        tipo = datos.get("tipo")
        if tipo and datos.get("nombre"):
            existe = SubAtencion.objects.filter(tipo=tipo, nombre__iexact=datos["nombre"])
            if self.instance.pk:
                existe = existe.exclude(pk=self.instance.pk)
            if existe.exists():
                self.add_error("nombre", "Ya existe una sub atención con este nombre en el tipo seleccionado.")
        if tipo and datos.get("activo") and not tipo.activo:
            self.add_error("activo", "No puede quedar activa si su Tipo de Atención está inactivo.")
        if self.instance.pk and tipo and tipo.pk != self.instance.tipo_id and self.instance.atenciones.exists():
            self.add_error("tipo", "No se puede cambiar el tipo: ya existen atenciones registradas con esta sub atención.")
        return datos


def _opciones_tipos(request):
    return [(t.pk, t.nombre) for t in TipoAtencion.objects.all()]


class SubAtencionesMantenedor(Mantenedor):
    modulo = "subatenciones"
    model = SubAtencion
    form_class = SubAtencionForm
    titulo = "Sub Atenciones"
    singular = "sub atención"
    femenino = True
    campos_busqueda = ["codigo", "nombre", "tipo__nombre", "tipo__codigo"]
    columnas = [
        Columna("Código", "codigo", "enlace"),
        Columna("Nombre", "nombre"),
        Columna("Tipo de Atención", "tipo.nombre"),
        Columna("Estado", "estado_texto", "estado"),
    ]
    columnas_excel = [("Código", "codigo"), ("Nombre", "nombre"), ("Código tipo", "tipo.codigo"),
                      ("Tipo de Atención", "tipo.nombre"), ("Estado", "estado_texto")]
    detalle = [("Código", "codigo"), ("Nombre", "nombre"), ("Tipo de Atención", "tipo"),
               ("Estado del tipo", "tipo.estado_texto"), ("Atenciones registradas", lambda s: s.atenciones.count())]
    filtros = [
        Filtro("tipo", "Tipo", _opciones_tipos, lambda qs, v: qs.filter(tipo_id=v)),
        filtro_estado(femenino=True),
    ]
    placeholder_busqueda = "Buscar por código, nombre o tipo…"

    def queryset(self, request):
        return SubAtencion.objects.select_related("tipo")

    def motivo_no_eliminar(self, request, obj):
        n = obj.atenciones.count()
        if n:
            return f"No se puede eliminar «{obj}»: tiene {n} atención(es) registradas. Puede desactivarla."
        return None

    def motivo_no_cambiar_estado(self, request, obj):
        if not obj.activo and not obj.tipo.activo:
            return f"No se puede activar «{obj}»: su Tipo de Atención «{obj.tipo.nombre}» está inactivo."
        return None


delegaciones = DelegacionesMantenedor()
items = ItemsMantenedor()
tipos = TiposMantenedor()
subatenciones = SubAtencionesMantenedor()
