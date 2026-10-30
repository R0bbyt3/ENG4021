from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_category_favorite_order_orderitem_productimage_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='document',
            field=models.CharField(blank=True, max_length=14, verbose_name='CPF ou CNPJ'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='legal_name',
            field=models.CharField(blank=True, max_length=150, verbose_name='razão social'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='location',
            field=models.CharField(blank=True, max_length=120, verbose_name='cidade e estado'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='segment',
            field=models.CharField(blank=True, max_length=20, verbose_name='atividade principal'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='social',
            field=models.CharField(blank=True, max_length=200, verbose_name='site ou Instagram'),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='terms_accepted_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='aceite dos termos'),
        ),
    ]
