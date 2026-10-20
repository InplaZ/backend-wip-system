from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def vincular_usuarios_existentes(apps, schema_editor):
    Movimiento = apps.get_model('wip', 'MovimientoWIP')
    Orden = apps.get_model('wip', 'OrdenProducto')
    Notificacion = apps.get_model('wip', 'NotificacionWIP')
    Usuario = apps.get_model(*settings.AUTH_USER_MODEL.split('.'))
    for movimiento in Movimiento.objects.all().iterator():
        updates = {}
        if movimiento.registrado_por:
            origin = Usuario.objects.filter(username__iexact=movimiento.registrado_por).first()
            if origin: updates['registrado_por_usuario_id'] = origin.pk
        recipient = None
        if movimiento.usuario_destino:
            recipient = Usuario.objects.filter(username__iexact=movimiento.usuario_destino, is_active=True).first()
            if recipient: updates['destinatario_id'] = recipient.pk
        if updates: Movimiento.objects.filter(pk=movimiento.pk).update(**updates)
        if recipient and movimiento.estado_recepcion == 'PENDIENTE':
            producto=Orden.objects.filter(pk=movimiento.producto_id).first()
            Notificacion.objects.get_or_create(
                usuario_id=recipient.pk,movimiento_id=movimiento.pk,
                tipo='MOVIMIENTO_RECIBIDO',
                defaults={
                    'titulo':f'Movimiento pendiente · ID {producto.id_producto if producto else movimiento.producto_id}',
                    'mensaje':f'{movimiento.area_origen} → {movimiento.area_destino} · {movimiento.cantidad_kg} kg · {movimiento.detalle_producto}',
                },
            )


class Migration(migrations.Migration):
    dependencies = [
        ('wip', '0005_registradopor'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='movimientowip', name='destinatario',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='movimientos_wip_recibidos', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='movimientowip', name='registrado_por_usuario',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='movimientos_wip_registrados', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='movimientowip', name='respondido_por_usuario',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='respuestas_wip_realizadas', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='movimientowip', name='fecha_respuesta',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='movimientowip', name='idempotency_key',
            field=models.UUIDField(blank=True, editable=False, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name='movimientowip', name='estado_recepcion',
            field=models.CharField(choices=[('PENDIENTE','Pendiente'),('ACEPTADO','Aceptado'),('OBSERVADO','Observado'),('NO_CONFORME','No conforme (legado)'),('RECHAZADO','Rechazado')], default='PENDIENTE', max_length=20),
        ),
        migrations.CreateModel(
            name='RespuestaMovimiento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('accion', models.CharField(choices=[('REGISTRADO','Registrado'),('ACEPTADO','Aceptado'),('OBSERVADO','Observado'),('RECHAZADO','Rechazado'),('REABIERTO','Reabierto')], max_length=20)),
                ('nombre_usuario', models.CharField(max_length=150)),
                ('comentario', models.TextField(blank=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('movimiento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='historial_respuestas', to='wip.movimientowip')),
                ('usuario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='historial_respuestas_wip', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering':['creado_en','id']},
        ),
        migrations.CreateModel(
            name='NotificacionWIP',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('MOVIMIENTO_RECIBIDO','Movimiento recibido'),('RESPUESTA_MOVIMIENTO','Respuesta del movimiento'),('MOVIMIENTO_REABIERTO','Movimiento reabierto')], max_length=30)),
                ('titulo', models.CharField(max_length=180)),
                ('mensaje', models.TextField()),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('fecha_lectura', models.DateTimeField(blank=True, null=True)),
                ('movimiento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notificaciones', to='wip.movimientowip')),
                ('respuesta', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='notificaciones', to='wip.respuestamovimiento')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notificaciones_wip', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering':['-creado_en','-id']},
        ),
        migrations.RunPython(vincular_usuarios_existentes, migrations.RunPython.noop),
        migrations.AddIndex(model_name='respuestamovimiento', index=models.Index(fields=['movimiento','creado_en'], name='wip_resp_movimie_3fc2f0_idx')),
        migrations.AddIndex(model_name='notificacionwip', index=models.Index(fields=['usuario','fecha_lectura','-creado_en'], name='wip_notif_user_read_idx')),
    ]
