from decimal import Decimal
from django.db.models import Sum, Q, Min, Max
from .models import MovimientoWIP

PROCESOS = ['PREPARADO', 'EXTRUSION', 'FLEXOGRAFIA', 'REFILADO', 'CONFECCION']

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
    resumen = {
      'materia_prima_kg': total('cantidad_kg', area_origen__iexact='PREPARADO'),
      'material_recuperado_kg': total('cantidad_kg', area_origen__iexact='RECICLADO'),
      'producto_terminado_kg': total('cantidad_kg', area_destino__iexact='AA TERMINADOS'),
      'producto_no_conforme_kg': total('cantidad_kg', area_destino__iexact='NO CONFORME'),
      'scrap_kg': decimal_or_zero(qs.aggregate(v=Sum('scrap_kg'))['v']),
      'almacen_kg': total('cantidad_kg', area_destino__iexact='ALMACEN'),
      'costo_movimientos_bs': sum(((m.costo_total_bs or Decimal('0')) for m in qs), Decimal('0')),
    }
    lead_time = (fechas['hasta'] - fechas['desde']).days if fechas['desde'] and fechas['hasta'] else 0
    return {'id_producto':str(id_producto),'desde':fechas['desde'],'hasta':fechas['hasta'],'lead_time_dias':lead_time,'resumen':resumen,'movimientos':qs}
