from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('wip', '0003_pedidos_trazabilidad_recepcion')]

    operations = [
        migrations.AddField('ordenproducto', 'codigo_producto_homologado', models.CharField(blank=True, max_length=120)),
        migrations.AddField('movimientowip', 'criticidad', models.CharField(choices=[('NORMAL','Normal'),('CRÍTICO','Crítico')], db_index=True, default='NORMAL', max_length=12)),
        migrations.AddField('movimientowip', 'evidencias', models.JSONField(blank=True, default=list)),
    ]
