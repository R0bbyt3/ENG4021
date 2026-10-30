from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_migrar_dados_defeito"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="product",
            name="product_valid_defect_scores",
        ),
        migrations.RemoveField(
            model_name="product",
            name="defect_extent",
        ),
        migrations.RemoveField(
            model_name="product",
            name="defect_location",
        ),
        migrations.RemoveField(
            model_name="product",
            name="defect_type",
        ),
    ]