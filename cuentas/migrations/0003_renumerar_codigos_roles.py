from django.db import migrations


def renumerar(apps, schema_editor):
    Rol = apps.get_model("cuentas", "Rol")
    for i, rol in enumerate(Rol.objects.order_by("pk"), start=1):
        rol.codigo = f"ROL-{i:05d}"
        rol.save(update_fields=["codigo"])


class Migration(migrations.Migration):
    dependencies = [("cuentas", "0002_usuario_cargo_usuario_debe_cambiar_clave_and_more")]
    operations = [migrations.RunPython(renumerar, migrations.RunPython.noop)]
