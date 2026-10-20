from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import OrdenProducto, MovimientoWIP, RespuestaMovimiento, NotificacionWIP

class OrdenProductoSerializer(serializers.ModelSerializer):
    id_producto = serializers.CharField(required=False, allow_blank=True)
    class Meta:
        model = OrdenProducto
        fields = ['id', 'id_producto', 'descripcion_referencia', 'cot_ref', 'cantidad_solicitada_kg', 'cantidad_solicitada_unidades', 'fecha_entrega', 'valor_pedido_bs', 'codigo_producto_homologado', 'activo']

class MovimientoWIPSerializer(serializers.ModelSerializer):
    id_producto = serializers.CharField(write_only=True, required=False)
    destinatario_id = serializers.PrimaryKeyRelatedField(source='destinatario', queryset=get_user_model().objects.filter(is_active=True), write_only=True, required=True)
    pedido = OrdenProductoSerializer(source='producto', read_only=True)
    producto_id = serializers.CharField(source='producto.id_producto', read_only=True)
    descripcion_referencia = serializers.CharField(source='producto.descripcion_referencia', read_only=True)
    ufe_calculada = serializers.DecimalField(max_digits=15, decimal_places=3, read_only=True)
    movimiento_almacen = serializers.DecimalField(max_digits=15, decimal_places=3, read_only=True)
    costo_total_bs = serializers.DecimalField(max_digits=20, decimal_places=4, read_only=True, allow_null=True)
    duracion_minutos = serializers.SerializerMethodField()
    registrado_por = serializers.CharField(read_only=True)
    entregado_por = serializers.CharField(read_only=True)
    recibido_por = serializers.CharField(read_only=True)
    usuario_destino = serializers.CharField(read_only=True)
    estado_recepcion = serializers.CharField(read_only=True)
    respuesta_recepcion = serializers.CharField(read_only=True)
    fecha_respuesta = serializers.DateTimeField(read_only=True)
    respondido_por = serializers.CharField(source='respondido_por_usuario.username', read_only=True, allow_null=True)
    tipo_movimiento = serializers.ChoiceField(choices=MovimientoWIP.TipoMovimiento.choices)
    class Meta:
        model = MovimientoWIP
        fields = ['id','fecha','fecha_inicio','fecha_fin','duracion_minutos','tipo_movimiento','criticidad','id_producto','producto_id','pedido','descripcion_referencia','detalle_producto','registrado_por','registrado_por_usuario','destinatario_id','entregado_por','cantidad_kg','ufe','scrap_kg','area_origen','area_destino','area_posterior','recibido_por','usuario_destino','estado_recepcion','respuesta_recepcion','respondido_por','fecha_respuesta','referencia_ht','codigo_talonario','codigo_producto_homologado','cot_ref','observaciones','evidencias','costo_bs_kg','ufe_calculada','movimiento_almacen','costo_total_bs','creado_en']
        read_only_fields = ['id','creado_en','registrado_por_usuario']
    def validate(self, attrs):
        inicio = attrs.get('fecha_inicio', getattr(self.instance, 'fecha_inicio', None))
        fin = attrs.get('fecha_fin', getattr(self.instance, 'fecha_fin', None))
        if inicio and fin and fin < inicio:
            raise serializers.ValidationError({'fecha_fin':'La fecha fin no puede ser anterior a la fecha inicio.'})
        id_producto = attrs.pop('id_producto', None)
        destinatario = attrs.get('destinatario')
        request = self.context.get('request')
        if destinatario is not None and request and destinatario.pk == request.user.pk:
            raise serializers.ValidationError({'destinatario_id':'El destinatario debe ser distinto del usuario que registra el movimiento.'})
        if id_producto is None and self.instance is not None:
            attrs['producto'] = self.instance.producto
            return attrs
        if not id_producto or not str(id_producto).strip():
            raise serializers.ValidationError({'id_producto':'El ID del producto es obligatorio.'})
        try:
            producto = OrdenProducto.objects.get(id_producto=str(id_producto).strip(), activo=True)
        except OrdenProducto.DoesNotExist:
            raise serializers.ValidationError({'id_producto':'No existe un producto/trabajo activo con ese ID. Importa o registra el ID antes de continuar.'})
        attrs['producto'] = producto
        previous = producto.movimientos.order_by('-id').first()
        if previous:
            from decimal import Decimal
            attrs['scrap_kg'] = max(Decimal('0'), previous.cantidad_kg - attrs.get('cantidad_kg', Decimal('0')))
            attrs['costo_bs_kg'] = None
        elif attrs.get('costo_bs_kg') is None:
            raise serializers.ValidationError({'costo_bs_kg':'El primer registro del pedido debe incluir el precio en Bs.'})
        if attrs.get('scrap_kg', 0) > attrs.get('cantidad_kg', 0) and attrs.get('cantidad_kg', 0) > 0:
            # Scrap may reflect a separate production loss, so do not reject; this warning-worthy case remains allowed.
            pass
        return attrs

    def get_duracion_minutos(self, obj):
        if not obj.fecha_inicio or not obj.fecha_fin:
            return None
        return round((obj.fecha_fin - obj.fecha_inicio).total_seconds() / 60, 1)

class UsuarioDestinatarioSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    nombre = serializers.CharField()
    grupos = serializers.ListField(child=serializers.CharField())

class ResponderMovimientoSerializer(serializers.Serializer):
    estado = serializers.ChoiceField(choices=[('ACEPTADO','Aceptado'),('OBSERVADO','Observado'),('RECHAZADO','Rechazado')])
    comentario = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)

    def validate(self, attrs):
        if attrs['estado'] in ['OBSERVADO','RECHAZADO'] and not attrs.get('comentario','').strip():
            field='comentario'
            label='La observación' if attrs['estado']=='OBSERVADO' else 'El motivo del rechazo'
            raise serializers.ValidationError({field:f'{label} es obligatorio.'})
        return attrs

class ReabrirMovimientoSerializer(serializers.Serializer):
    comentario = serializers.CharField(trim_whitespace=True)
    def validate_comentario(self, value):
        if not value.strip(): raise serializers.ValidationError('Indica la corrección o gestión realizada antes de reenviar.')
        return value

class RespuestaMovimientoHistorialSerializer(serializers.ModelSerializer):
    class Meta:
        model=RespuestaMovimiento
        fields=['id','accion','usuario','nombre_usuario','comentario','creado_en']
        read_only_fields=fields

class NotificacionWIPSerializer(serializers.ModelSerializer):
    movimiento_detalle = MovimientoWIPSerializer(source='movimiento', read_only=True)
    respuesta_detalle = RespuestaMovimientoHistorialSerializer(source='respuesta', read_only=True)
    historial_respuestas = serializers.SerializerMethodField()
    no_leida = serializers.SerializerMethodField()
    class Meta:
        model=NotificacionWIP
        fields=['id','tipo','titulo','mensaje','creado_en','fecha_lectura','no_leida','movimiento','movimiento_detalle','respuesta_detalle','historial_respuestas']
        read_only_fields=fields
    def get_no_leida(self,obj): return obj.fecha_lectura is None
    def get_historial_respuestas(self,obj): return RespuestaMovimientoHistorialSerializer(obj.movimiento.historial_respuestas.all(),many=True).data
