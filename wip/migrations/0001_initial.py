# Generated for the initial INPLAZ WIP schema.
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='OrdenProducto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('id_producto', models.CharField(db_index=True, max_length=60, unique=True)),
                ('descripcion_referencia', models.CharField(blank=True, max_length=255)),
                ('activo', models.BooleanField(default=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name':'ID de producto/trabajo','verbose_name_plural':'IDs de producto/trabajo','ordering':['id_producto']},
        ),
        migrations.CreateModel(
            name='MovimientoWIP',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateField(db_index=True)),
                ('tipo_movimiento', models.CharField(choices=[('INGRESO','Ingreso'),('SALIDA','Salida'),('TRASPASO','Traspaso')], db_index=True, max_length=12)),
                ('detalle_producto', models.CharField(max_length=255)),
                ('cantidad_kg', models.DecimalField(decimal_places=3, max_digits=14, validators=[django.core.validators.MinValueValidator(0)])),
                ('ufe', models.DecimalField(decimal_places=3, max_digits=14, validators=[django.core.validators.MinValueValidator(0)])),
                ('scrap_kg', models.DecimalField(decimal_places=3, default=0, max_digits=14, validators=[django.core.validators.MinValueValidator(0)])),
                ('area_origen', models.CharField(max_length=80)),
                ('area_destino', models.CharField(max_length=80)),
                ('area_posterior', models.CharField(blank=True, max_length=80)),
                ('entregado_por', models.CharField(max_length=120)),
                ('recibido_por', models.CharField(max_length=120)),
                ('referencia_ht', models.CharField(blank=True, max_length=120)),
                ('observaciones', models.TextField(blank=True)),
                ('costo_bs_kg', models.DecimalField(blank=True, decimal_places=4, max_digits=14, null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('producto', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='movimientos', to='wip.ordenproducto')),
            ],
            options={'verbose_name':'Movimiento WIP','verbose_name_plural':'Movimientos WIP','ordering':['fecha','id']},
        ),
        migrations.AddIndex(model_name='movimientowip', index=models.Index(fields=['producto','fecha'], name='wip_movim_producto_6d0a3f_idx')),
        migrations.AddIndex(model_name='movimientowip', index=models.Index(fields=['fecha','tipo_movimiento'], name='wip_movim_fecha_3b6e2a_idx')),
        migrations.AddIndex(model_name='movimientowip', index=models.Index(fields=['area_origen','fecha'], name='wip_movim_area_or_15d4aa_idx')),
    ]
