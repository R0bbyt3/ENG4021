from django.db import migrations


def copiar_defeitos_existentes(apps, schema_editor):
    """Cria um Defeito para cada Product já cadastrado, usando os valores
    que hoje estão nos campos defect_type/defect_location/defect_extent,
    antes desses campos serem removidos de Product na próxima migração."""
    Product = apps.get_model("core", "Product")
    Defeito = apps.get_model("core", "Defeito")
    Defeito.objects.bulk_create([
        Defeito(
            product=product,
            tipo=product.defect_type,
            localizacao=product.defect_location,
            extensao=product.defect_extent,
        )
        for product in Product.objects.all()
    ])


def recriar_campos_em_product(apps, schema_editor):
    """Reversão: copia os valores de volta para os campos de Product."""
    Product = apps.get_model("core", "Product")
    Defeito = apps.get_model("core", "Defeito")
    for defeito in Defeito.objects.select_related("product"):
        Product.objects.filter(pk=defeito.product_id).update(
            defect_type=defeito.tipo,
            defect_location=defeito.localizacao,
            defect_extent=defeito.extensao,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_criar_model_defeito"),
    ]

    operations = [
        migrations.RunPython(copiar_defeitos_existentes, recriar_campos_em_product),
    ]