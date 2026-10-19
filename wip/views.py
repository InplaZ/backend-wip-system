from datetime import date
from django.db.models import Q, Count, Sum
from django.http import HttpResponse
from rest_framework import generics, filters, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from .models import OrdenProducto, MovimientoWIP
from .serializers import OrdenProductoSerializer, MovimientoWIPSerializer
from .services import reporte_diario, reporte_por_id
from rest_framework.permissions import AllowAny

class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            'status': 'ok',
            'service': 'INPLAZ WIP API'
        })

class ProductoSearchView(APIView):
    def get(self, request):
        term = (request.query_params.get('id') or '').strip()
        if not term: return Response({'detail':'Envía el parámetro id.'}, status=400)
        try: obj = OrdenProducto.objects.get(id_producto=term, activo=True)
        except OrdenProducto.DoesNotExist: return Response({'detail':'No se encontró un ID de producto/trabajo activo.'}, status=404)
        data = OrdenProductoSerializer(obj).data
        data['ultimo_detalle'] = obj.movimientos.order_by('-fecha','-id').values_list('detalle_producto',flat=True).first() or obj.descripcion_referencia
        return Response(data)

class ProductoListCreateView(generics.ListCreateAPIView):
    queryset = OrdenProducto.objects.all().order_by('id_producto')
    serializer_class = OrdenProductoSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['id_producto','descripcion_referencia']

class MovimientoListCreateView(generics.ListCreateAPIView):
    serializer_class = MovimientoWIPSerializer
    def get_queryset(self):
        qs = MovimientoWIP.objects.select_related('producto').all()
        p = self.request.query_params
        if p.get('id'): qs = qs.filter(producto__id_producto=p['id'].strip())
        if p.get('fecha'): qs = qs.filter(fecha=p['fecha'])
        if p.get('desde'): qs = qs.filter(fecha__gte=p['desde'])
        if p.get('hasta'): qs = qs.filter(fecha__lte=p['hasta'])
        if p.get('tipo'): qs = qs.filter(tipo_movimiento=p['tipo'])
        if p.get('area'): qs = qs.filter(Q(area_origen__icontains=p['area'])|Q(area_destino__icontains=p['area'])|Q(area_posterior__icontains=p['area']))
        return qs.order_by('-fecha','-id')

class MovimientoDetailView(generics.RetrieveAPIView):
    queryset = MovimientoWIP.objects.select_related('producto').all()
    serializer_class = MovimientoWIPSerializer

class ReporteIDView(APIView):
    def get(self, request):
        id_producto = (request.query_params.get('id') or '').strip()
        if not id_producto: raise ValidationError({'id':'El ID es obligatorio.'})
        desde, hasta = request.query_params.get('desde'), request.query_params.get('hasta')
        try:
            result = reporte_por_id(id_producto, desde, hasta)
            if not result['movimientos'].exists():
                return Response({'id_producto':id_producto,'desde':None,'hasta':None,'lead_time_dias':0,'resumen':{},'movimientos':[]})
            result['movimientos'] = MovimientoWIPSerializer(result['movimientos'], many=True).data
            return Response(result)
        except ValueError as exc: raise ValidationError({'detail':str(exc)})

class ReporteDiarioView(APIView):
    def get(self, request):
        raw = request.query_params.get('fecha')
        if not raw: raise ValidationError({'fecha':'Selecciona una fecha.'})
        try: fecha = date.fromisoformat(raw)
        except ValueError: raise ValidationError({'fecha':'Formato esperado: AAAA-MM-DD.'})
        result = reporte_diario(fecha)
        result['movimientos'] = MovimientoWIPSerializer(result['movimientos'], many=True).data
        return Response(result)

class ImportarCatalogoView(APIView):
    """Importación de IDs desde un CSV UTF-8 con columnas id_producto,descripcion_referencia."""
    def post(self, request):
        import csv, io
        archivo = request.FILES.get('archivo')
        if not archivo: raise ValidationError({'archivo':'Adjunta un CSV.'})
        try: rows = csv.DictReader(io.StringIO(archivo.read().decode('utf-8-sig')))
        except UnicodeDecodeError: raise ValidationError({'archivo':'El CSV debe estar codificado en UTF-8.'})
        creados = actualizados = 0
        for row in rows:
            pid = (row.get('id_producto') or row.get('ID') or row.get('id') or '').strip()
            desc = (row.get('descripcion_referencia') or row.get('DETALLE PRODUCTO') or row.get('detalle_producto') or '').strip()
            if not pid: continue
            _, created = OrdenProducto.objects.update_or_create(id_producto=pid, defaults={'descripcion_referencia':desc,'activo':True})
            creados += int(created); actualizados += int(not created)
        return Response({'creados':creados,'actualizados':actualizados}, status=status.HTTP_200_OK)
