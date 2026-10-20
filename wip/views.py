from datetime import date
import uuid
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q, Count, Sum
from django.http import HttpResponse
from rest_framework import generics, filters, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from .models import OrdenProducto, MovimientoWIP, NotificacionWIP
from .serializers import (OrdenProductoSerializer, MovimientoWIPSerializer,
    UsuarioDestinatarioSerializer, ResponderMovimientoSerializer,
    ReabrirMovimientoSerializer, NotificacionWIPSerializer)
from .services import reporte_diario, reporte_por_id, registrar_movimiento, responder_movimiento, reabrir_movimiento
from rest_framework.permissions import AllowAny

class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            'status': 'ok',
            'service': 'INPLAZ WIP API'
        })

class UsuarioActualView(APIView):
    def get(self, request):
        return Response({'id':request.user.pk,'username':request.user.username,'nombre':request.user.get_full_name().strip() or request.user.username})

class UsuarioDestinatarioListView(APIView):
    def get(self, request):
        users=get_user_model().objects.filter(is_active=True).exclude(pk=request.user.pk).prefetch_related('groups').order_by('first_name','last_name','username')
        data=[{'id':u.pk,'username':u.username,'nombre':u.get_full_name().strip() or u.username,'grupos':list(u.groups.values_list('name',flat=True))} for u in users]
        return Response(UsuarioDestinatarioSerializer(data,many=True).data)

class ProductoSearchView(APIView):
    def get(self, request):
        term = (request.query_params.get('id') or '').strip()
        if not term: return Response({'detail':'Envía el parámetro id.'}, status=400)
        try: obj = OrdenProducto.objects.get(id_producto=term, activo=True)
        except OrdenProducto.DoesNotExist: return Response({'detail':'No se encontró un ID de producto/trabajo activo.'}, status=404)
        data = OrdenProductoSerializer(obj).data
        data['ultimo_detalle'] = obj.movimientos.order_by('-fecha','-id').values_list('detalle_producto',flat=True).first() or obj.descripcion_referencia
        data['movimientos_count'] = obj.movimientos.count()
        return Response(data)

class ProductoListCreateView(generics.ListCreateAPIView):
    queryset = OrdenProducto.objects.all().order_by('id_producto')
    serializer_class = OrdenProductoSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['id_producto','descripcion_referencia']

class MovimientoListCreateView(generics.ListCreateAPIView):
    serializer_class = MovimientoWIPSerializer
    def create(self, request, *args, **kwargs):
        raw_key=request.headers.get('Idempotency-Key')
        try: key=uuid.UUID(raw_key) if raw_key else None
        except (ValueError,TypeError): raise ValidationError({'Idempotency-Key':'Debe ser un UUID válido.'})
        serializer=self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        movement,created=registrar_movimiento(serializer,request.user,key)
        return Response(self.get_serializer(movement).data,status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    def get_queryset(self):
        username=self.request.user.username
        qs = MovimientoWIP.objects.select_related('producto','registrado_por_usuario','destinatario').filter(
            Q(registrado_por_usuario=self.request.user) |
            Q(destinatario=self.request.user) |
            Q(registrado_por__iexact=username) |
            Q(usuario_destino__iexact=username)
        )
        p = self.request.query_params
        if p.get('id'): qs = qs.filter(producto__id_producto=p['id'].strip())
        if p.get('fecha'): qs = qs.filter(fecha=p['fecha'])
        if p.get('desde'): qs = qs.filter(fecha__gte=p['desde'])
        if p.get('hasta'): qs = qs.filter(fecha__lte=p['hasta'])
        if p.get('tipo'): qs = qs.filter(tipo_movimiento=p['tipo'])
        if p.get('criticidad'): qs = qs.filter(criticidad=p['criticidad'])
        if p.get('search'):
            term = p['search'].strip()
            qs = qs.filter(Q(producto__id_producto__icontains=term)|Q(detalle_producto__icontains=term)|Q(entregado_por__icontains=term)|Q(recibido_por__icontains=term)|Q(referencia_ht__icontains=term)|Q(codigo_talonario__icontains=term)|Q(area_origen__icontains=term)|Q(area_destino__icontains=term)|Q(observaciones__icontains=term))
        if p.get('area'): qs = qs.filter(Q(area_origen__icontains=p['area'])|Q(area_destino__icontains=p['area'])|Q(area_posterior__icontains=p['area']))
        if p.get('para'): qs = qs.filter(Q(destinatario=self.request.user)|Q(usuario_destino__iexact=username))
        if p.get('estado_recepcion'): qs = qs.filter(estado_recepcion=p['estado_recepcion'])
        return qs.order_by('-fecha','-id')

class MovimientoDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = MovimientoWIPSerializer
    http_method_names = ['get', 'head', 'options']
    def get_queryset(self):
        username=self.request.user.username
        return MovimientoWIP.objects.select_related('producto','registrado_por_usuario','destinatario').filter(Q(registrado_por_usuario=self.request.user)|Q(destinatario=self.request.user)|Q(registrado_por__iexact=username)|Q(usuario_destino__iexact=username))

class ResponderMovimientoView(APIView):
    def post(self,request,pk):
        serializer=ResponderMovimientoSerializer(data=request.data);serializer.is_valid(raise_exception=True)
        movimiento=responder_movimiento(pk,request.user,serializer.validated_data['estado'],serializer.validated_data.get('comentario',''))
        return Response(MovimientoWIPSerializer(movimiento).data)

class ReabrirMovimientoView(APIView):
    def post(self,request,pk):
        serializer=ReabrirMovimientoSerializer(data=request.data);serializer.is_valid(raise_exception=True)
        movimiento=reabrir_movimiento(pk,request.user,serializer.validated_data['comentario'])
        return Response(MovimientoWIPSerializer(movimiento).data)

class NotificacionListView(generics.ListAPIView):
    serializer_class=NotificacionWIPSerializer
    def get_queryset(self):
        qs=NotificacionWIP.objects.filter(usuario=self.request.user).select_related('movimiento__producto','movimiento__registrado_por_usuario','movimiento__destinatario','respuesta').prefetch_related('movimiento__historial_respuestas__usuario')
        unread=self.request.query_params.get('no_leidas','').lower() in ['1','true','yes']
        return qs.filter(fecha_lectura__isnull=True) if unread else qs

class NotificacionLeerView(APIView):
    def post(self,request,pk):
        notification=get_object_or_404(NotificacionWIP.objects.filter(usuario=request.user),pk=pk)
        if notification.fecha_lectura is None:
            notification.fecha_lectura=timezone.now();notification.save(update_fields=['fecha_lectura'])
        return Response(NotificacionWIPSerializer(notification).data)

class ReporteIDView(APIView):
    def get(self, request):
        id_producto = (request.query_params.get('id') or '').strip()
        if not id_producto: raise ValidationError({'id':'El ID es obligatorio.'})
        desde, hasta = request.query_params.get('desde'), request.query_params.get('hasta')
        try:
            result = reporte_por_id(id_producto, desde, hasta)
            if not result['movimientos']:
                return Response({'id_producto':id_producto,'desde':None,'hasta':None,'lead_time_dias':0,'lead_time_minutos':None,'perdidas_por_area':[],'tiempos_por_area':[],'resumen':{},'movimientos':[]})
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
