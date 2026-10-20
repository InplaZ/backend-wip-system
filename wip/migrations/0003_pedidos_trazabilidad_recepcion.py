import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('wip', '0002_rename_wip_movim_producto_6d0a3f_idx_wip_movimie_product_1ec898_idx_and_more')]

    operations = [
        migrations.AddField('ordenproducto', 'cot_ref', models.CharField(blank=True, max_length=120)),
        migrations.AddField('ordenproducto', 'cantidad_solicitada_kg', models.DecimalField(blank=True, decimal_places=3, max_digits=14, null=True, validators=[django.core.validators.MinValueValidator(0)])),
        migrations.AddField('ordenproducto', 'cantidad_solicitada_unidades', models.PositiveIntegerField(blank=True, null=True)),
        migrations.AddField('ordenproducto', 'fecha_entrega', models.DateField(blank=True, null=True)),
        migrations.AddField('ordenproducto', 'valor_pedido_bs', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True, validators=[django.core.validators.MinValueValidator(0)])),
        migrations.AddField('movimientowip', 'fecha_inicio', models.DateTimeField(blank=True, null=True)),
        migrations.AddField('movimientowip', 'fecha_fin', models.DateTimeField(blank=True, null=True)),
        migrations.AddField('movimientowip', 'usuario_destino', models.CharField(blank=True, max_length=150)),
        migrations.AddField('movimientowip', 'estado_recepcion', models.CharField(choices=[('PENDIENTE','Pendiente'),('ACEPTADO','Aceptado'),('NO_CONFORME','No conforme'),('RECHAZADO','Rechazado')], default='PENDIENTE', max_length=20)),
        migrations.AddField('movimientowip', 'respuesta_recepcion', models.TextField(blank=True)),
        migrations.AddField('movimientowip', 'codigo_talonario', models.CharField(blank=True, max_length=120)),
        migrations.AddField('movimientowip', 'codigo_producto_homologado', models.CharField(blank=True, max_length=120)),
        migrations.AddField('movimientowip', 'cot_ref', models.CharField(blank=True, max_length=120)),
    ]
