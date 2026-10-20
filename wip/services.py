from decimal import Decimal
from django.db import IntegrityError, transaction
from django.db.models import Sum, Q, Min, Max
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from .models import MovimientoWIP, RespuestaMovimiento, NotificacionWIP

PROCESOS = ['PREPARADO', 'EXTRUSION', 'FLEXOGRAFIA', 'REFILADO', 'CONFECCION', 'A. TERMINADOS']

def _nombre_usuario(user):
    return user.get_full_name().strip() or user.username

def registrar_movimiento(serializer, usuario, idempotency_key=None):
    """Create a movement, its audit event and recipient notification atomically."""
    try:
        with transaction.atomic():
            if idempotency_key:
                existing = MovimientoWIP.objects.filter(idempotency_key=idempotency_key, registrado_por_usuario=usuario).first()
                if existing: return existing, False
            destinatario = serializer.validated_data['destinatario']
            movimiento = serializer.save(
                registrado_por=usuario.username,
                registrado_por_usuario=usuario,
                destinatario=destinatario,
                usuario_destino=destinatario.username,
                entregado_por=_nombre_usuario(usuario),
                recibido_por=_nombre_usuario(destinatario),
                idempotency_key=idempotency_key,
                estado_recepcion=MovimientoWIP._meta.get_field('estado_recepcion').default,
            )
            evento = RespuestaMovimiento.objects.create(
                movimiento=movimiento, accion=RespuestaMovimiento.Accion.REGISTRADO,
                usuario=usuario, nombre_usuario=_nombre_usuario(usuario),
                comentario='Movimiento registrado y enviado al destinatario.',
            )
            NotificacionWIP.objects.create(
                usuario=destinatario, movimiento=movimiento, respuesta=evento,
                tipo=NotificacionWIP.Tipo.MOVIMIENTO_RECIBIDO,
                titulo=f'Nuevo movimiento para ID {movimiento.producto.id_producto}',
                mensaje=f'{movimiento.area_origen} → {movimiento.area_destino} · {movimiento.cantidad_kg} kg · {movimiento.detalle_producto}',
            )
            return movimiento, True
    except IntegrityError:
        if idempotency_key:
            existing = MovimientoWIP.objects.filter(idempotency_key=idempotency_key, registrado_por_usuario=usuario).first()
            if existing: return existing, False
            if MovimientoWIP.objects.filter(idempotency_key=idempotency_key).exists():
                raise ValidationError({'Idempotency-Key':'Esta clave ya fue utilizada por otra cuenta.'})
        raise

def responder_movimiento(movimiento_id, usuario, estado, comentario=''):
    if estado not in [RespuestaMovimiento.Accion.ACEPTADO, RespuestaMovimiento.Accion.OBSERVADO, RespuestaMovimiento.Accion.RECHAZADO]:
        raise ValidationError({'estado':'La acción indicada no es válida.'})
    comentario = (comentario or '').strip()
    if estado in [RespuestaMovimiento.Accion.OBSERVADO, RespuestaMovimiento.Accion.RECHAZADO] and not comentario:
        raise ValidationError({'comentario':'La observación o el motivo de rechazo es obligatorio.'})
    with transaction.atomic():
        movimiento = MovimientoWIP.objects.select_for_update(of=('self',)).select_related('producto','registrado_por_usuario','destinatario').get(pk=movimiento_id)
        if movimiento.destinatario_id != usuario.pk:
            raise PermissionDenied('Solo el usuario destinatario asignado puede responder este movimiento.')
        if movimiento.estado_recepcion != 'PENDIENTE':
            raise ValidationError({'estado':'El movimiento ya fue respondido. Solo puede volver a responderse si el usuario de origen lo reabre.'})
        movimiento.estado_recepcion = estado
        movimiento.respuesta_recepcion = comentario
        movimiento.respondido_por_usuario = usuario
        movimiento.fecha_respuesta = timezone.now()
        movimiento.save(update_fields=['estado_recepcion','respuesta_recepcion','respondido_por_usuario','fecha_respuesta','actualizado_en'])
        evento = RespuestaMovimiento.objects.create(movimiento=movimiento,accion=estado,usuario=usuario,nombre_usuario=_nombre_usuario(usuario),comentario=comentario)
        origen = movimiento.registrado_por_usuario
        if origen:
            NotificacionWIP.objects.create(
                usuario=origen,movimiento=movimiento,respuesta=evento,
                tipo=NotificacionWIP.Tipo.RESPUESTA_MOVIMIENTO,
                titulo=f'Movimiento {estado.lower()} · ID {movimiento.producto.id_producto}',
                mensaje=comentario or f'{_nombre_usuario(usuario)} aceptó el movimiento {movimiento.area_origen} → {movimiento.area_destino}.',
            )
        return movimiento

def reabrir_movimiento(movimiento_id, usuario, comentario):
    comentario=(comentario or '').strip()
    if not comentario: raise ValidationError({'comentario':'Describe la corrección o gestión antes de reenviar.'})
    with transaction.atomic():
        movimiento=MovimientoWIP.objects.select_for_update(of=('self',)).select_related('producto','registrado_por_usuario','destinatario').get(pk=movimiento_id)
        if movimiento.registrado_por_usuario_id != usuario.pk:
            raise PermissionDenied('Solo el usuario que registró el movimiento puede gestionar la observación.')
        if movimiento.estado_recepcion != 'OBSERVADO':
            raise ValidationError({'estado':'Solo los movimientos observados pueden corregirse y reenviarse.'})
        movimiento.estado_recepcion='PENDIENTE'
        movimiento.respuesta_recepcion=''
        movimiento.respondido_por_usuario=None
        movimiento.fecha_respuesta=None
        movimiento.save(update_fields=['estado_recepcion','respuesta_recepcion','respondido_por_usuario','fecha_respuesta','actualizado_en'])
        evento=RespuestaMovimiento.objects.create(movimiento=movimiento,accion=RespuestaMovimiento.Accion.REABIERTO,usuario=usuario,nombre_usuario=_nombre_usuario(usuario),comentario=comentario)
        if movimiento.destinatario:
            NotificacionWIP.objects.create(
                usuario=movimiento.destinatario,movimiento=movimiento,respuesta=evento,
                tipo=NotificacionWIP.Tipo.MOVIMIENTO_REABIERTO,
                titulo=f'Movimiento corregido y reenviado · ID {movimiento.producto.id_producto}',
                mensaje=comentario,
            )
        return movimiento

def decimal_or_zero(value): return value if value is not None else Decimal('0')

def reporte_diario(fecha):
    qs = MovimientoWIP.objects.filter(fecha=fecha).select_related('producto').order_by('id')
    def sums(field, **filters):
        return decimal_or_zero(qs.filter(**filters).aggregate(v=Sum(field))['v'])
    procesos = []
    for area in PROCESOS:
        procesos.append({'proceso':area,'kg':sums('cantidad_kg', area_origen__iexact=area),'ufe':sums('ufe', area_origen__iexact=area),'scrap':sums('scrap_kg', area_origen__iexact=area)})
    procesos += [
        {'proceso':'ALMACEN (INGRESO)','kg':sums('cantidad_kg',area_destino__iexact='ALMACEN'),'ufe':sums('ufe',area_destino__iexact='ALMACEN'),'scrap':sums('scrap_kg',area_posterior__iexact='ALMACEN')},
        {'proceso':'ALMACEN (SALIDA)','kg':sums('cantidad_kg',area_origen__iexact='ALMACEN'),'ufe':sums('ufe',area_origen__iexact='ALMACEN'),'scrap':sums('scrap_kg',area_origen__iexact='ALMACEN')},
        {'proceso':'NO CONFORMES','kg':sums('cantidad_kg',area_destino__iexact='NO CONFORME'),'ufe':sums('ufe',area_origen__iexact='NO CONFORME'),'scrap':sums('scrap_kg',area_origen__iexact='NO CONFORME')},
        {'proceso':'RECUPERADO','kg':sums('cantidad_kg',area_origen__iexact='RECICLADO'),'ufe':sums('ufe',area_origen__iexact='RECUPERADO'),'scrap':sums('scrap_kg',area_origen__iexact='RECUPERADO')},
    ]
    total_produccion = sum((x['kg'] for x in procesos if x['proceso'] in PROCESOS + ['RECUPERADO']), Decimal('0'))
    return {'fecha':fecha,'movimientos':qs,'procesos':procesos,'total_produccion_kg':total_produccion,'total_scrap_kg':decimal_or_zero(qs.aggregate(v=Sum('scrap_kg'))['v']),'total_no_conforme_kg':sums('cantidad_kg',area_destino__iexact='NO CONFORME')}

def reporte_por_id(id_producto, desde=None, hasta=None):
    qs = MovimientoWIP.objects.filter(producto__id_producto=str(id_producto)).select_related('producto')
    if desde: qs = qs.filter(fecha__gte=desde)
    if hasta: qs = qs.filter(fecha__lte=hasta)
    qs = qs.order_by('fecha','id')
    def total(field, **filters): return decimal_or_zero(qs.filter(**filters).aggregate(v=Sum(field))['v'])
    fechas = qs.aggregate(desde=Min('fecha'), hasta=Max('fecha'))
    terminados = decimal_or_zero(qs.filter(Q(area_destino__iexact='AA TERMINADOS') | Q(area_destino__iexact='A. TERMINADOS')).aggregate(v=Sum('cantidad_kg'))['v'])
    resumen = {
      'materia_prima_kg': total('cantidad_kg', area_origen__iexact='PREPARADO'),
      'material_recuperado_kg': total('cantidad_kg', area_origen__iexact='RECICLADO'),
      'producto_terminado_kg': terminados,
      'producto_no_conforme_kg': total('cantidad_kg', area_destino__iexact='NO CONFORME'),
      'scrap_kg': decimal_or_zero(qs.aggregate(v=Sum('scrap_kg'))['v']),
      'almacen_kg': total('cantidad_kg', area_destino__iexact='ALMACEN'),
      'costo_movimientos_bs': sum(((m.costo_total_bs or Decimal('0')) for m in qs), Decimal('0')),
    }
    lead_time = (fechas['hasta'] - fechas['desde']).days if fechas['desde'] and fechas['hasta'] else 0
    perdidas_por_area = []
    tiempos_por_area = []
    for area in qs.order_by().values_list('area_origen', flat=True).distinct():
        area_qs = qs.filter(area_origen=area)
        scrap = decimal_or_zero(area_qs.aggregate(v=Sum('scrap_kg'))['v'])
        if scrap:
            perdidas_por_area.append({'area': area, 'scrap_kg': scrap})
        duraciones = [m for m in area_qs if m.fecha_inicio and m.fecha_fin]
        minutos = sum((m.fecha_fin - m.fecha_inicio).total_seconds() / 60 for m in duraciones)
        tiempos_por_area.append({'area': area, 'minutos': round(minutos, 1), 'movimientos_con_tiempo': len(duraciones)})
    movimientos = list(qs)
    con_inicio = [m.fecha_inicio for m in movimientos if m.fecha_inicio]
    con_fin = [m.fecha_fin for m in movimientos if m.fecha_fin]
    lead_time_minutos = round((max(con_fin) - min(con_inicio)).total_seconds() / 60, 1) if con_inicio and con_fin else None
    return {'id_producto':str(id_producto),'desde':fechas['desde'],'hasta':fechas['hasta'],'lead_time_dias':lead_time,'lead_time_minutos':lead_time_minutos,'perdidas_por_area':perdidas_por_area,'tiempos_por_area':tiempos_por_area,'resumen':resumen,'movimientos':movimientos}
