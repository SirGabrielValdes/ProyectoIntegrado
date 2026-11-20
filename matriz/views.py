from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils import timezone

from catalogos.models import COMUNA_POR_DEFECTO, Delegacion, Item
from core.crud import Columna, Filtro, FormularioBase, Mantenedor, filtro_estado
from core.permisos import requiere_permiso
from cuentas.models import CARGOS, Usuario

from . import semaforo
from .models import Actividad, Ausencia, MetaTrimestre, Organizacion, Trimestre
from .reglas import MAX_ACTIVIDADES_DIA, calcular_puntaje, errores_de_fecha, limite_ingreso

EXTENSIONES_RESPALDO = (".pdf", ".jpg", ".jpeg", ".png")
MAX_ARCHIVO = 5 * 1024 * 1024


def campo_fecha(**attrs):
    return forms.DateInput(format="%Y-%m-%d", attrs={"type": "date", **attrs})


def equipo(request):
    """Funcionarios activos con cargo de la delegación activa."""
    return Usuario.objects.filter(delegaciones=request.delegacion_activa, is_active=True).exclude(cargo="")


# =============================================================================
# Trimestres y metas
# =============================================================================
class TrimestreForm(FormularioBase):
    class Meta:
        model = Trimestre
        fields = ["nombre", "inicio", "fin", "estado"]
        widgets = {"inicio": campo_fecha(), "fin": campo_fecha()}

    unicos = {"nombre": "Ya existe un trimestre con este nombre."}

    def clean(self):
        datos = super().clean()
        inicio, fin, estado = datos.get("inicio"), datos.get("fin"), datos.get("estado")
        if inicio and fin:
            if fin <= inicio:
                self.add_error("fin", "La fecha de término debe ser posterior a la de inicio.")
            else:
                cruce = Trimestre.objects.filter(inicio__lte=fin, fin__gte=inicio).exclude(pk=self.instance.pk).first()
                if cruce:
                    self.add_error("inicio", f"Las fechas se superponen con «{cruce}».")
        if estado == "ABIERTO":
            otro = Trimestre.objects.filter(estado="ABIERTO").exclude(pk=self.instance.pk).first()
            if otro:
                self.add_error("estado", f"Ya hay un trimestre abierto («{otro}»). Ciérrelo antes de abrir otro.")
        return datos


class TrimestresMantenedor(Mantenedor):
    modulo = "trimestres"
    model = Trimestre
    form_class = TrimestreForm
    titulo = "Trimestres de evaluación"
    singular = "trimestre"
    campo_estado = None
    plantilla_detalle = "matriz/trimestre_detalle.html"
    campos_busqueda = ["codigo", "nombre"]
    columnas = [
        Columna("Código", "codigo", "enlace"),
        Columna("Nombre", "nombre"),
        Columna("Inicio", "inicio"),
        Columna("Término", "fin"),
        Columna("Días hábiles", "dias_habiles"),
        Columna("Estado", "estado_texto"),
        Columna("Actividades", lambda t: t.actividades.count()),
    ]
    columnas_excel = [("Código", "codigo"), ("Nombre", "nombre"), ("Inicio", "inicio"), ("Término", "fin"),
                      ("Días hábiles", "dias_habiles"), ("Estado", "estado_texto"),
                      ("Metas definidas", lambda t: t.metas.count()), ("Actividades", lambda t: t.actividades.count())]
    detalle = [("Código", "codigo"), ("Nombre", "nombre"), ("Inicio", "inicio"), ("Término", "fin"),
               ("Días hábiles", "dias_habiles"), ("Estado", "estado_texto"),
               ("Actividades registradas", lambda t: t.actividades.count())]
    filtros = [Filtro("estado", "Estado", lambda r: Trimestre.ESTADOS, lambda qs, v: qs.filter(estado=v))]
    placeholder_busqueda = "Buscar por código o nombre…"
    ayuda_lista = "Solo puede haber un trimestre abierto; en él se registran las actividades de la matriz."

    def motivo_no_eliminar(self, request, obj):
        n = obj.actividades.count()
        if n:
            return f"No se puede eliminar «{obj}»: tiene {n} actividad(es) registradas. Puede cerrarlo."
        return None

    def contexto_extra(self, request, obj=None):
        if obj is None:
            return {}
        metas = obj.metas.select_related("item")
        return {"metas": metas, "cargos": dict(CARGOS)}

    def vista_metas(self, request, pk):
        trimestre = self.obtener(request, pk)
        items = list(Item.objects.filter(activo=True))
        actuales = {(m.item_id, m.cargo): m for m in trimestre.metas.all()}
        errores = []
        if request.method == "POST":
            nuevos = {}
            for item in items:
                for cargo, _ in CARGOS:
                    valor = request.POST.get(f"meta_{item.pk}_{cargo}", "").strip()
                    if valor == "":
                        valor = "0"
                    if not valor.isdigit() or int(valor) > 999:
                        errores.append(f"{item.nombre} / {dict(CARGOS)[cargo]}: ingrese un número entero entre 0 y 999.")
                    else:
                        nuevos[(item.pk, cargo)] = int(valor)
            if not errores:
                with transaction.atomic():
                    for (item_id, cargo), cantidad in nuevos.items():
                        meta = actuales.get((item_id, cargo))
                        if cantidad == 0 and meta:
                            meta.delete()
                        elif cantidad and meta and meta.cantidad != cantidad:
                            meta.cantidad = cantidad
                            meta.save(update_fields=["cantidad"])
                        elif cantidad and not meta:
                            MetaTrimestre.objects.create(trimestre=trimestre, item_id=item_id, cargo=cargo,
                                                         cantidad=cantidad)
                messages.success(request, f"Metas de «{trimestre}» actualizadas correctamente.")
                return redirect(self.url("detalle", trimestre.pk))
            messages.error(request, "Revise los valores marcados: " + " ".join(errores[:3]))
        filas = []
        for item in items:
            celdas = []
            for cargo, nombre in CARGOS:
                clave = f"meta_{item.pk}_{cargo}"
                valor = request.POST.get(clave) if request.method == "POST" else (
                    actuales[(item.pk, cargo)].cantidad if (item.pk, cargo) in actuales else "")
                celdas.append({"nombre": clave, "valor": valor, "cargo": nombre})
            filas.append({"item": item, "celdas": celdas})
        return render(request, "matriz/metas.html", {
            **self.contexto_base(request), "obj": trimestre, "filas": filas, "cargos": CARGOS})

    def urls(self):
        patrones, nombre = super().urls()
        patrones.append(path("<int:pk>/metas/", requiere_permiso("trimestres.ver", "trimestres.editar")(
            self.vista_metas), name="metas"))
        return patrones, nombre


# =============================================================================
# Organizaciones comunitarias
# =============================================================================
class OrganizacionForm(FormularioBase):
    class Meta:
        model = Organizacion
        fields = ["nombre", "tipo", "subtipo", "delegacion", "direccion", "comuna", "dirigente", "telefono", "activo"]
        labels = {"activo": "Activa"}

    unicos = {"nombre": "Ya existe una organización con este nombre."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["delegacion"].queryset = Delegacion.objects.filter(
            pk__in=[d.pk for d in self.request.delegaciones_autorizadas])
        self.fields["delegacion"].empty_label = "Seleccione una delegación…"
        if not self.instance.pk:
            self.initial.setdefault("comuna", COMUNA_POR_DEFECTO)
            self.initial.setdefault("delegacion", self.request.delegacion_activa.pk)


def _opciones_tipo_org(request):
    return Organizacion.TIPOS


class OrganizacionesMantenedor(Mantenedor):
    modulo = "organizaciones"
    model = Organizacion
    form_class = OrganizacionForm
    titulo = "Juntas de vecinos y organizaciones"
    singular = "organización"
    femenino = True
    campos_busqueda = ["codigo", "nombre", "subtipo", "dirigente", "direccion"]
    columnas = [
        Columna("Código", "codigo", "enlace"),
        Columna("Nombre", "nombre"),
        Columna("Tipo", lambda o: o.get_tipo_display()),
        Columna("Delegación", "delegacion.codigo"),
        Columna("Dirigente", "dirigente"),
        Columna("Teléfono", "telefono"),
        Columna("Estado", "estado_texto", "estado"),
    ]
    columnas_excel = [("Código", "codigo"), ("Nombre", "nombre"), ("Tipo", lambda o: o.get_tipo_display()),
                      ("Subtipo", "subtipo"), ("Delegación", "delegacion"), ("Dirección", "direccion"),
                      ("Comuna", "comuna"), ("Dirigente", "dirigente"), ("Teléfono", "telefono"),
                      ("Estado", "estado_texto")]
    detalle = [("Código", "codigo"), ("Nombre", "nombre"), ("Tipo", lambda o: o.get_tipo_display()),
               ("Subtipo", "subtipo"), ("Delegación", "delegacion"), ("Dirección", "direccion"),
               ("Comuna", "comuna"), ("Dirigente o contacto", "dirigente"), ("Teléfono", "telefono"),
               ("Actividades registradas", lambda o: o.actividades.count())]
    filtros = [Filtro("tipo", "Tipo", _opciones_tipo_org, lambda qs, v: qs.filter(tipo=v)),
               filtro_estado(femenino=True)]
    placeholder_busqueda = "Buscar por nombre, código, dirigente o dirección…"
    ayuda_lista = "Organizaciones de la delegación activa."

    def queryset(self, request):
        return Organizacion.objects.select_related("delegacion").filter(delegacion=request.delegacion_activa)

    def motivo_no_eliminar(self, request, obj):
        n = obj.actividades.count()
        if n:
            return f"No se puede eliminar «{obj}»: tiene {n} actividad(es) asociadas. Puede desactivarla."
        return None


# =============================================================================
# Actividades de la matriz
# =============================================================================
class ActividadForm(FormularioBase):
    destinatario = forms.ModelChoiceField(
        label="Funcionario felicitado", queryset=Usuario.objects.none(), required=False,
        help_text="Solo para felicitaciones: a quién se dirige el reconocimiento.")

    class Meta:
        model = Actividad
        fields = ["item", "fecha", "tipo_registro", "solicitante_tipo", "organizacion", "nombre_contacto",
                  "telefono_contacto", "descripcion", "destinatario", "respaldo"]
        widgets = {"descripcion": forms.Textarea, "fecha": campo_fecha(),
                   "tipo_registro": forms.RadioSelect, "solicitante_tipo": forms.RadioSelect}

    minimos = {"descripcion": 10}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        usuario = self.request.user
        self.puede_felicitar = usuario.tiene_permiso("actividades.aprobar")
        items = Item.objects.filter(activo=True)
        if not self.puede_felicitar:
            items = items.exclude(es_felicitacion=True)
        self.fields["item"].queryset = items
        self.fields["item"].empty_label = "Seleccione el ítem de la matriz…"
        self.fields["organizacion"].queryset = Organizacion.objects.filter(
            delegacion=self.request.delegacion_activa, activo=True)
        self.fields["organizacion"].empty_label = "Sin organización"
        self.fields["destinatario"].queryset = equipo(self.request)
        self.fields["destinatario"].empty_label = "Seleccione el funcionario felicitado…"
        self.fields["destinatario"].widget.attrs["class"] = "campo-select"
        hoy = timezone.localdate()
        self.fields["fecha"].widget.attrs["max"] = hoy.isoformat()
        self.initial.setdefault("fecha", hoy)
        self.fields["respaldo"].help_text = "Obligatorio en felicitaciones: PDF o imagen (máx. 5 MB)."
        self.fields["nombre_contacto"].help_text = "Sin nombre y teléfono la actividad no suma puntaje."
        self.items_felicitacion = list(items.filter(es_felicitacion=True).values_list("pk", flat=True))

    def clean_respaldo(self):
        archivo = self.cleaned_data.get("respaldo")
        if archivo and hasattr(archivo, "size"):
            if not archivo.name.lower().endswith(EXTENSIONES_RESPALDO):
                raise ValidationError("El respaldo debe ser PDF, JPG o PNG.")
            if archivo.size > MAX_ARCHIVO:
                raise ValidationError("El respaldo no puede superar 5 MB.")
        return archivo

    def clean(self):
        datos = super().clean()
        usuario, hoy = self.request.user, timezone.localdate()
        fecha, item = datos.get("fecha"), datos.get("item")
        self.trimestre = Trimestre.abierto()
        if not self.trimestre:
            raise ValidationError("No hay un trimestre abierto: no se pueden registrar actividades.")
        if fecha:
            for error in errores_de_fecha(fecha, hoy):
                self.add_error("fecha", error)
            if not self.trimestre.contiene(fecha):
                self.add_error("fecha", f"La fecha está fuera del trimestre abierto ({self.trimestre.inicio:%d-%m-%Y} "
                                        f"al {self.trimestre.fin:%d-%m-%Y}).")
        self.funcionario = usuario
        if item and item.es_felicitacion:
            if not self.puede_felicitar:
                self.add_error("item", "Las felicitaciones solo las registra el delegado.")
            if not datos.get("respaldo"):
                self.add_error("respaldo", "Adjunte el respaldo formal de la felicitación.")
            if not datos.get("destinatario"):
                self.add_error("destinatario", "Indique a qué funcionario se dirige la felicitación.")
            else:
                self.funcionario = datos["destinatario"]
        if datos.get("solicitante_tipo") == "ORGANIZACION" and not datos.get("organizacion"):
            self.add_error("organizacion", "Seleccione la organización solicitante.")
        if fecha and not self.errors:
            del_dia = Actividad.objects.filter(funcionario=self.funcionario, fecha=fecha).count()
            if del_dia >= MAX_ACTIVIDADES_DIA:
                self.add_error("fecha", f"Ya hay {del_dia} actividades registradas el {fecha:%d-%m-%Y}: el máximo "
                                        f"diario es {MAX_ACTIVIDADES_DIA}.")
        return datos


def _opciones_item(request):
    return [(i.pk, i.nombre) for i in Item.objects.all()]


def _opciones_trimestre(request):
    return [(t.pk, t.nombre) for t in Trimestre.objects.all()]


class ActividadesMantenedor(Mantenedor):
    modulo = "actividades"
    model = Actividad
    form_class = ActividadForm
    titulo = "Matriz de actividades"
    singular = "actividad"
    femenino = True
    campo_estado = None
    plantilla_form = "matriz/actividad_form.html"
    plantilla_detalle = "matriz/actividad_detalle.html"
    campos_busqueda = ["codigo", "descripcion", "nombre_contacto", "funcionario__nombre", "item__nombre",
                       "organizacion__nombre"]
    columnas = [
        Columna("Código", "codigo", "enlace"),
        Columna("Fecha", "fecha"),
        Columna("Funcionario", "funcionario.nombre"),
        Columna("Ítem", "item.nombre"),
        Columna("Tipo", lambda a: "Ejecutada" if a.tipo_registro == "EJECUTADA" else "Coordinación"),
        Columna("Puntaje", "puntaje"),
        Columna("Observación", lambda a: a.motivo_sin_puntaje or "Suma 1 punto"),
    ]
    columnas_excel = [("Código", "codigo"), ("Trimestre", "trimestre.nombre"), ("Fecha", "fecha"),
                      ("Funcionario", "funcionario.nombre"), ("Cargo", lambda a: a.funcionario.get_cargo_display()),
                      ("Delegación", "delegacion"), ("Ítem", "item.nombre"),
                      ("Tipo de registro", lambda a: a.get_tipo_registro_display()),
                      ("Solicitante", lambda a: a.get_solicitante_tipo_display()), ("Organización", "organizacion"),
                      ("Nombre contacto", "nombre_contacto"), ("Teléfono contacto", "telefono_contacto"),
                      ("Descripción", "descripcion"), ("Puntaje", "puntaje"), ("Motivo sin puntaje", "motivo_sin_puntaje"),
                      ("Registrado por", "registrado_por.nombre")]
    detalle = [("Código", "codigo"), ("Trimestre", "trimestre"), ("Fecha de la actividad", "fecha"),
               ("Funcionario", "funcionario"), ("Registrado por", "registrado_por"), ("Delegación", "delegacion"),
               ("Ítem", "item"), ("Tipo de registro", lambda a: a.get_tipo_registro_display()),
               ("Solicitante", lambda a: a.get_solicitante_tipo_display()), ("Organización", "organizacion"),
               ("Nombre del vecino o usuario", "nombre_contacto"), ("Teléfono", "telefono_contacto"),
               ("Descripción", "descripcion"), ("Puntaje", "puntaje_texto"),
               ("Motivo sin puntaje", "motivo_sin_puntaje"), ("Registrada el", "creado")]
    filtros = [
        Filtro("trimestre", "Trimestre", _opciones_trimestre, lambda qs, v: qs.filter(trimestre_id=v)),
        Filtro("item", "Ítem", _opciones_item, lambda qs, v: qs.filter(item_id=v)),
        Filtro("puntaje", "Puntaje", lambda r: [("1", "Suman punto"), ("0", "Sin puntaje")],
               lambda qs, v: qs.filter(puntaje=int(v))),
    ]
    placeholder_busqueda = "Buscar por código, descripción, vecino, funcionario u organización…"

    @property
    def ayuda_lista(self):
        return (f"Máximo {MAX_ACTIVIDADES_DIA} actividades por día. La semana (lunes a viernes) se cierra el lunes "
                "siguiente. Solo suman punto las acciones ejecutadas con nombre y teléfono del vecino.")

    def queryset(self, request):
        qs = Actividad.objects.select_related("funcionario", "item", "trimestre", "organizacion", "delegacion",
                                              "registrado_por").filter(delegacion=request.delegacion_activa)
        if not request.user.tiene_permiso("actividades.aprobar"):
            qs = qs.filter(funcionario=request.user)
        return qs

    def contexto_base(self, request, **extra):
        ctx = super().contexto_base(request, **extra)
        ctx["nuevo_texto"] = "Registrar actividad"
        ctx["trimestre_abierto"] = Trimestre.abierto()
        return ctx

    def guardar(self, request, form, creando):
        actividad = form.save(commit=False)
        actividad.trimestre = form.trimestre
        actividad.funcionario = form.funcionario
        actividad.registrado_por = request.user
        actividad.delegacion = request.delegacion_activa
        actividad.puntaje, actividad.motivo_sin_puntaje = calcular_puntaje(actividad)
        actividad.save()
        if actividad.puntaje:
            messages.info(request, f"La actividad {actividad.codigo} suma 1 punto en «{actividad.item.nombre}».")
        else:
            messages.warning(request, f"La actividad {actividad.codigo} quedó registrada sin puntaje: "
                                      f"{actividad.motivo_sin_puntaje}")
        return actividad

    def motivo_no_eliminar(self, request, obj):
        if timezone.localdate() > limite_ingreso(obj.fecha):
            return "La semana de esta actividad está cerrada: ya no se puede eliminar."
        if obj.funcionario_id != request.user.pk and obj.registrado_por_id != request.user.pk \
                and not request.user.tiene_permiso("actividades.aprobar"):
            return "Solo puede eliminar sus propias actividades."
        if hasattr(obj, "compromisos") and obj.compromisos.exists():
            return "La actividad fue derivada al tubo de trabajo: no se puede eliminar."
        return None

    def vista_respaldo(self, request, pk):
        actividad = self.obtener(request, pk)
        if not actividad.respaldo:
            raise Http404("La actividad no tiene respaldo.")
        return FileResponse(actividad.respaldo.open("rb"), as_attachment=False,
                            filename=actividad.respaldo.name.rsplit("/", 1)[-1])

    def urls(self):
        patrones, nombre = super().urls()
        patrones.append(path("<int:pk>/respaldo/", requiere_permiso("actividades.ver")(self.vista_respaldo),
                             name="respaldo"))
        return patrones, nombre


# =============================================================================
# Ausencias (pestaña del semáforo)
# =============================================================================
class AusenciaForm(FormularioBase):
    class Meta:
        model = Ausencia
        fields = ["funcionario", "tipo", "desde", "hasta", "motivo"]
        widgets = {"desde": campo_fecha(), "hasta": campo_fecha()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["funcionario"].queryset = equipo(self.request)
        self.fields["funcionario"].empty_label = "Seleccione un funcionario…"

    def clean(self):
        datos = super().clean()
        f, desde, hasta = datos.get("funcionario"), datos.get("desde"), datos.get("hasta")
        if desde and hasta:
            if hasta < desde:
                self.add_error("hasta", "La fecha «hasta» no puede ser anterior a «desde».")
            elif f:
                cruce = Ausencia.objects.filter(funcionario=f, desde__lte=hasta, hasta__gte=desde).exclude(
                    pk=self.instance.pk).first()
                if cruce:
                    self.add_error("desde", f"Se superpone con otra ausencia registrada: {cruce}.")
        return datos


class AusenciasMantenedor(Mantenedor):
    modulo = "ausencias"
    model = Ausencia
    form_class = AusenciaForm
    titulo = "Ausencias del equipo (semáforo)"
    singular = "ausencia"
    femenino = True
    campo_estado = None
    campos_busqueda = ["funcionario__nombre", "motivo"]
    columnas = [
        Columna("Funcionario", "funcionario.nombre", "enlace"),
        Columna("Tipo", lambda a: a.get_tipo_display()),
        Columna("Desde", "desde"),
        Columna("Hasta", "hasta"),
        Columna("Días hábiles", "dias"),
        Columna("Registrada por", "registrado_por.nombre"),
    ]
    columnas_excel = [("Funcionario", "funcionario.nombre"), ("Tipo", lambda a: a.get_tipo_display()),
                      ("Desde", "desde"), ("Hasta", "hasta"), ("Días hábiles", "dias"), ("Observación", "motivo"),
                      ("Registrada por", "registrado_por.nombre")]
    detalle = [("Funcionario", "funcionario"), ("Tipo", lambda a: a.get_tipo_display()), ("Desde", "desde"),
               ("Hasta", "hasta"), ("Días hábiles", "dias"), ("Observación", "motivo"),
               ("Registrada por", "registrado_por")]
    filtros = [Filtro("tipo", "Tipo", lambda r: Ausencia.TIPOS, lambda qs, v: qs.filter(tipo=v))]
    placeholder_busqueda = "Buscar por funcionario u observación…"
    ayuda_lista = "Las ausencias las ingresa el delegado y ajustan automáticamente las metas del semáforo."

    def queryset(self, request):
        return Ausencia.objects.select_related("funcionario", "registrado_por").filter(
            funcionario__delegaciones=request.delegacion_activa).distinct()

    def guardar(self, request, form, creando):
        ausencia = form.save(commit=False)
        if creando:
            ausencia.registrado_por = request.user
        ausencia.save()
        return ausencia


# =============================================================================
# Dashboards y semáforo
# =============================================================================
def _trimestre(request):
    trimestres = list(Trimestre.objects.all())
    elegido = request.GET.get("trimestre", "")
    actual = next((t for t in trimestres if str(t.pk) == elegido), None) or Trimestre.abierto() or (
        trimestres[0] if trimestres else None)
    return actual, trimestres


def _contexto(request, **extra):
    trimestre, trimestres = _trimestre(request)
    u = request.user
    pestanas = [
        ("general", "General (todas las delegaciones)", reverse("dashboard:general"), u.tiene_permiso("dash_general.ver")),
        ("delegacion", "Por delegación", reverse("dashboard:delegacion"), u.tiene_permiso("dash_delegacion.ver")),
        ("funcionario", "Por funcionario", reverse("dashboard:funcionario"), u.tiene_permiso("dash_funcionario.ver")),
    ]
    return {"trimestre": trimestre, "trimestres": trimestres, "semaforo": semaforo.SEMAFORO,
            "pestanas": pestanas, **extra}


@requiere_permiso("dash_general.ver")
def dashboard_general(request):
    ctx = _contexto(request, vista="general")
    if ctx["trimestre"]:
        ctx["resumen"] = semaforo.resumen_general(ctx["trimestre"], request.delegaciones_autorizadas)
    return render(request, "matriz/dashboard_general.html", ctx)


@requiere_permiso("dash_delegacion.ver")
def dashboard_delegacion(request):
    ctx = _contexto(request, vista="delegacion")
    if ctx["trimestre"]:
        ctx["resumen"] = semaforo.resumen_delegacion(request.delegacion_activa, ctx["trimestre"])
    return render(request, "matriz/dashboard_delegacion.html", ctx)


@requiere_permiso("dash_funcionario.ver")
def dashboard_funcionario(request):
    ctx = _contexto(request, vista="funcionario")
    elegido = request.GET.get("funcionario", "")
    funcionario = request.user
    if elegido and elegido != str(request.user.pk):
        # Ver a otro funcionario exige permiso de equipo y que pertenezca a la delegación activa.
        if not request.user.tiene_permiso("dash_delegacion.ver"):
            raise PermissionDenied("Solo puede ver su propio semáforo.")
        funcionario = get_object_or_404(equipo(request), pk=elegido) if elegido.isdigit() else None
        if funcionario is None:
            raise Http404
    ctx["funcionario"] = funcionario
    ctx["equipo"] = list(equipo(request)) if request.user.tiene_permiso("dash_delegacion.ver") else []
    if ctx["trimestre"]:
        ctx["resumen"] = semaforo.resumen_funcionario(funcionario, ctx["trimestre"])
        ctx["ausencias"] = Ausencia.objects.filter(funcionario=funcionario, hasta__gte=ctx["trimestre"].inicio,
                                                   desde__lte=ctx["trimestre"].fin)
    return render(request, "matriz/dashboard_funcionario.html", ctx)


trimestres = TrimestresMantenedor()
organizaciones = OrganizacionesMantenedor()
actividades = ActividadesMantenedor()
ausencias = AusenciasMantenedor()
