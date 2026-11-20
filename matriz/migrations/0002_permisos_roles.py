from django.db import migrations

# Permisos de los módulos de la Etapa 3 para los roles base ya existentes
# (instalaciones en uso). Se agregan sin quitar los permisos personalizados,
# salvo el del antiguo módulo «seguimiento», reemplazado por el Tubo de trabajo.
NUEVOS_MODULOS = ("trimestres", "organizaciones", "actividades", "ausencias", "tubo", "areas",
                  "dash_general", "dash_delegacion", "dash_funcionario")


def actualizar(apps, schema_editor):
    from core.permisos import ROLES_BASE

    Rol = apps.get_model("cuentas", "Rol")
    for datos in ROLES_BASE.values():
        rol = Rol.objects.filter(nombre=datos["nombre"]).first()
        if rol is None or rol.es_sistema:
            continue
        nuevos = [p for p in datos["permisos"] if p.split(".")[0] in NUEVOS_MODULOS]
        permisos = [p for p in (rol.permisos or []) if not p.startswith("seguimiento.")]
        rol.permisos = permisos + [p for p in nuevos if p not in permisos]
        rol.save(update_fields=["permisos"])


class Migration(migrations.Migration):
    dependencies = [("matriz", "0001_initial"), ("cuentas", "0003_renumerar_codigos_roles")]
    operations = [migrations.RunPython(actualizar, migrations.RunPython.noop)]
