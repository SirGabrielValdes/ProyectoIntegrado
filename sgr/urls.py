from django.urls import include, path

from atenciones.views import atenciones
from catalogos.views import delegaciones, items, subatenciones, tipos
from core import views as core
from cuentas import views as cuentas
from cuentas.views import roles, usuarios

urls_cuentas = ([
    path("ingresar/", cuentas.ingresar, name="login"),
    path("salir/", cuentas.salir, name="logout"),
    path("recuperar/", cuentas.solicitar_codigo, name="recuperar"),
    path("recuperar/validar/", cuentas.validar_codigo, name="validar_codigo"),
    path("recuperar/reenviar/", cuentas.reenviar_codigo, name="reenviar_codigo"),
    path("recuperar/nueva-clave/", cuentas.nueva_clave, name="nueva_clave"),
], "cuentas")

urls_core = ([
    path("", core.inicio, name="inicio"),
    path("contexto/delegacion/", core.cambiar_delegacion, name="cambiar_delegacion"),
    path("modulo/<slug:modulo>/", core.pendiente, name="pendiente"),
    path("salud/", core.salud, name="salud"),
], "core")

urlpatterns = [
    path("", include(urls_core)),
    path("cuenta/", include(urls_cuentas)),
    path("delegaciones/", include(delegaciones.urls())),
    path("roles/", include(roles.urls())),
    path("usuarios/", include(usuarios.urls())),
    path("items/", include(items.urls())),
    path("tipos-atencion/", include(tipos.urls())),
    path("sub-atenciones/", include(subatenciones.urls())),
    path("atenciones/", include(atenciones.urls())),
]

handler403 = "core.views.error_403"
handler404 = "core.views.error_404"
handler500 = "core.views.error_500"
