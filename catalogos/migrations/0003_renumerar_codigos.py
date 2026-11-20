from django.db import migrations

# Renumera los códigos existentes al formato automático PREFIJO-00000,
# en el orden en que fueron creados.
MODELOS = [("Delegacion", "DEL"), ("Item", "ITM"), ("TipoAtencion", "TAT"), ("SubAtencion", "SAT")]


def renumerar(apps, schema_editor):
    for nombre, prefijo in MODELOS:
        modelo = apps.get_model("catalogos", nombre)
        for i, obj in enumerate(modelo.objects.order_by("pk"), start=1):
            obj.codigo = f"{prefijo}-{i:05d}"
            obj.save(update_fields=["codigo"])


class Migration(migrations.Migration):
    dependencies = [("catalogos", "0002_item_ambito_item_es_felicitacion_and_more")]
    operations = [migrations.RunPython(renumerar, migrations.RunPython.noop)]
