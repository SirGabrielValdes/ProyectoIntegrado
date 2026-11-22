from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.urls import path
from django.views.decorators.http import require_POST

from atenciones.models import Atencion
from core.crud import Columna, Filtro, FormularioBase, Mantenedor, filtro_estado
from core.permisos import requiere_permiso
from cuentas.models import Usuario
from matriz.models import Actividad

from . import servicios
from .models import AreaApoyo, Compromiso, Evidencia


# =============================================================================
# Áreas de apoyo
# =============================================================================
class AreaApoyoForm(FormularioBase):
    class Meta:
        model = AreaApoyo
        fields = ["nombre", "descripcion", "activo"]
        labels = {"activo": "Activa"}

    unicos = {"nombre": "Ya existe un área con este nombre."}


class AreasMantenedor(Mantenedor):
    modulo = "areas"
    model = AreaApoyo
    form_class = AreaApoyoForm
    titulo = "Áreas municipales de apoyo"
    singular = "área de apoyo"
    femenino = True
    campos_busqueda = ["codigo", "nombre", "descripcion"]
    columnas = [Columna("Código", "codigo", "enlace"), Columna("Nombre", "nombre"),
                Columna("Descripción", "descripcion"), Columna("Estado", "estado_texto", "estado")]
    columnas_excel = [("Código", "codigo"), ("Nombre", "nombre"), ("Descripción", "descripcion"),
                      ("Estado", "estado_texto")]
    detalle = [("Código", "codigo"), ("Nombre", "nombre"), ("Descripción", "descripcion"),
               ("Compromisos asociados", lambda a: a.compromisos.count())]
    filtros = [filtro_estado(femenino=True)]

    def motivo_no_eliminar(self, request, obj):
        n = obj.compromisos.count()
        return f"No se puede eliminar «{obj}»: tiene {n} compromiso(s). Puede desactivarla." if n else None


# =============================================================================
# Compromisos del tubo
# =============================================================================
class CompromisoForm(FormularioBase):
    class Meta:
        model = Compromiso
        fields = ["titulo", "solicitante", "descripcion", "responsable", "area_apoyo"]
        widgets = {"descripcion": forms.Textarea}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["responsable"].queryset = Usuario.objects.filter(
            delegaciones=self.request.delegacion_activa, is_active=True).order_by("nombre")
        self.fields["responsable"].empty_label = "Seleccione un responsable…"
        self.fields["area_apoyo"].queryset = AreaApoyo.objects.filter(activo=True)
        self.fields["area_apoyo"].empty_label = "Sin área de apoyo"
        self.origen = None
        datos = self.request.GET if self.request.method == "GET" else self.request.POST
        if datos.get("actividad", "").isdigit():
            self.origen = Actividad.objects.filter(pk=datos["actividad"],
                                                   delegacion=self.request.delegacion_activa).first()
        elif datos.get("atencion", "").isdigit():
            self.origen = Atencion.objects.filter(pk=datos["atencion"],
                                                  delegacion=self.request.delegacion_activa).first()
        if self.origen is not None and not self.is_bound:
            if isinstance(self.origen, Actividad):
                self.initial.update({"titulo": f"[{self.origen.codigo}] {self.origen.item.nombre}",
                                     "solicitante": self.origen.nombre_contacto or str(self.origen.organizacion or ""),
                                     "descripcion": self.origen.descripcion})
            else:
                self.initial.update({"titulo": f"[{self.origen.folio}] {self.origen.subatencion.nombre}",
                                     "solicitante": self.origen.vecino.nombre,
                                     "descripcion": self.origen.descripcion})
            self.initial.setdefault("responsable", self.request.user.pk)


def _opciones_estado(request):
    return Compromiso.ESTADOS


def _opciones_responsable(request):
    return [(u.pk, u.nombre) for u in Usuario.objects.filter(delegaciones=request.delegacion_activa).order_by("nombre")]


class CompromisosMantenedor(Mantenedor):
    modulo = "tubo"
    model = Compromiso
    form_class = CompromisoForm
    titulo = "Tubo de trabajo"
    singular = "compromiso"
    campo_estado = None
    permite_editar = False
    plantilla_form = "tubo/form.html"
    campos_busqueda = ["codigo", "titulo", "solicitante", "descripcion", "responsable__nombre",
                       "area_apoyo__nombre", "actividad__codigo"]
    columnas = [
        Columna("Código", "codigo", "enlace"),
        Columna("Referencia", "referencia"),
        Columna("Compromiso", "titulo"),
        Columna("Solicitante", "solicitante"),
        Columna("Apoyo", "area_apoyo.nombre"),
        Columna("Responsable", "responsable.nombre"),
        Columna("Estado", "estado_texto"),
    ]
    columnas_excel = [("Código", "codigo"), ("Referencia", "referencia"), ("Compromiso", "titulo"),
                      ("Solicitante", "solicitante"), ("Detalle", "descripcion"), ("Área de apoyo", "area_apoyo"),
                      ("Responsable", "responsable.nombre"), ("Estado", "estado_texto"),
                      ("Evidencias aprobadas", lambda c: c.evidencias.filter(estado="APROBADA").count()),
                      ("Ingresado", "creado"), ("Realizado", lambda c: c.realizado_en or "")]
    filtros = [Filtro("estado", "Estado", _opciones_estado, lambda qs, v: qs.filter(estado=v)),
               Filtro("responsable", "Responsable", _opciones_responsable, lambda qs, v: qs.filter(responsable_id=v))]
    placeholder_busqueda = "Buscar por código, compromiso, solicitante, responsable o área…"

    def queryset(self, request):
        return Compromiso.objects.select_related("responsable", "area_apoyo", "actividad", "atencion").filter(
            delegacion=request.delegacion_activa)

    def contexto_base(self, request, **extra):
        ctx = super().contexto_base(request, **extra)
        ctx["nuevo_texto"] = "Ingresar compromiso"
        return ctx

    def guardar(self, request, form, creando):
        compromiso = form.save(commit=False)
        compromiso.delegacion = request.delegacion_activa
        compromiso.creado_por = request.user
        if isinstance(form.origen, Actividad):
            compromiso.actividad = form.origen
        elif isinstance(form.origen, Atencion):
            compromiso.atencion = form.origen
        compromiso.save()
        servicios.registrar_ingreso(compromiso, request.user)
        return compromiso

    # --- Tablero Kanban ----------------------------------------------------
    def vista_tablero(self, request):
        qs = self.queryset(request)
        q = " ".join(request.GET.get("q", "").split())[:100]
        if q:
            qs = qs.filter(Q(codigo__icontains=q) | Q(titulo__icontains=q) | Q(solicitante__icontains=q)
                           | Q(responsable__nombre__icontains=q))
        if request.GET.get("responsable", "").isdigit():
            qs = qs.filter(responsable_id=request.GET["responsable"])
        conteo = dict(self.queryset(request).values_list("estado").annotate(n=Count("id")))
        total = sum(conteo.values())
        realizados = conteo.get("REALIZADO", 0)
        titulos = {"INGRESADO": "Ingresados", "PENDIENTE": "Pendientes", "EN_PROCESO": "En proceso",
                   "REALIZADO": "Realizados"}
        columnas = [{"estado": e, "nombre": titulos[e], "items": [c for c in qs if c.estado == e]}
                    for e, _ in Compromiso.ESTADOS]
        ctx = self.contexto_base(
            request, columnas=columnas, q=q, responsables=_opciones_responsable(request),
            responsable_sel=request.GET.get("responsable", ""),
            indicadores={"total": total, "realizados": realizados,
                         "tasa": (100 * realizados / total) if total else 0,
                         "en_proceso": conteo.get("EN_PROCESO", 0), "pendientes": conteo.get("PENDIENTE", 0),
                         "ingresados": conteo.get("INGRESADO", 0)})
        return render(request, "tubo/tablero.html", ctx)

    # --- Ficha con historial y evidencias ------------------------------------
    def vista_detalle(self, request, pk):
        obj = self.obtener(request, pk)
        ctx = self.contexto_base(request, obj=obj, historial=obj.historial.select_related("usuario"),
                                 evidencias=obj.evidencias.select_related("subida_por", "revisada_por"),
                                 puede_aprobar=request.user.tiene_permiso("tubo.aprobar"))
        return render(request, "tubo/detalle.html", ctx)

    def vista_avanzar(self, request, pk):
        obj = self.obtener(request, pk)
        try:
            obj = servicios.avanzar(obj, request.user, request.POST.get("comentario", ""),
                                    destino=request.POST.get("destino") or None)
        except ValidationError as e:
            messages.error(request, " ".join(e.messages))
        else:
            messages.success(request, f"Compromiso {obj.codigo} movido a «{obj.estado_texto}».")
        return redirect(request.POST.get("volver") == "tablero" and self.url("lista") or self.url("detalle", obj.pk))

    def vista_subir_evidencia(self, request, pk):
        obj = self.obtener(request, pk)
        try:
            servicios.subir_evidencia(obj, request.user, request.FILES.get("foto"),
                                      request.POST.get("descripcion", ""))
        except ValidationError as e:
            messages.error(request, " ".join(e.messages))
        else:
            messages.success(request, "Evidencia cargada. Queda pendiente de revisión del delegado.")
        return redirect(self.url("detalle", obj.pk))

    def _evidencia(self, request, pk, ev):
        obj = self.obtener(request, pk)
        try:
            return obj, obj.evidencias.get(pk=ev)
        except Evidencia.DoesNotExist:
            raise Http404

    def vista_revisar_evidencia(self, request, pk, ev):
        obj, evidencia = self._evidencia(request, pk, ev)
        aprobar = request.POST.get("decision") == "aprobar"
        try:
            servicios.revisar_evidencia(evidencia, request.user, aprobar, request.POST.get("comentario", ""))
        except ValidationError as e:
            messages.error(request, " ".join(e.messages))
        else:
            messages.success(request, "Evidencia aprobada." if aprobar else "Evidencia rechazada.")
        return redirect(self.url("detalle", obj.pk))

    def vista_foto(self, request, pk, ev):
        _, evidencia = self._evidencia(request, pk, ev)
        return FileResponse(evidencia.foto.open("rb"))

    def urls(self):
        ver = requiere_permiso("tubo.ver")
        editar = lambda v: require_POST(requiere_permiso("tubo.ver", "tubo.editar")(v))  # noqa: E731
        patrones = [
            path("", ver(self.vista_tablero), name="lista"),
            path("tabla/", ver(self.vista_lista), name="tabla"),
            path("nuevo/", requiere_permiso("tubo.ver", "tubo.crear")(self.vista_crear), name="crear"),
            path("exportar/", requiere_permiso("tubo.ver", "tubo.exportar")(self.vista_exportar), name="exportar"),
            path("<int:pk>/", ver(self.vista_detalle), name="detalle"),
            path("<int:pk>/avanzar/", editar(self.vista_avanzar), name="avanzar"),
            path("<int:pk>/evidencias/", editar(self.vista_subir_evidencia), name="subir_evidencia"),
            path("<int:pk>/evidencias/<int:ev>/revisar/",
                 require_POST(requiere_permiso("tubo.ver", "tubo.aprobar")(self.vista_revisar_evidencia)),
                 name="revisar_evidencia"),
            path("<int:pk>/evidencias/<int:ev>/foto/", ver(self.vista_foto), name="foto"),
        ]
        return patrones, "tubo"


areas = AreasMantenedor()
compromisos = CompromisosMantenedor()
