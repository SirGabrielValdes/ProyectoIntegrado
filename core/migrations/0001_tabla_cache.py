from django.core.management import call_command
from django.db import migrations


def crear_tabla_cache(apps, schema_editor):
    # La caché (límite de intentos de login) usa una tabla de base de datos.
    # Se crea aquí para que basta con ejecutar `migrate`.
    call_command("createcachetable", database=schema_editor.connection.alias, verbosity=0)


class Migration(migrations.Migration):
    dependencies = []

    operations = [migrations.RunPython(crear_tabla_cache, migrations.RunPython.noop)]
