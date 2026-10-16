from rest_framework import serializers
from .models import OrdenProducto, MovimientoWIP

class OrdenProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrdenProducto
        fields = ['id', 'id_producto', 'descripcion_referencia', 'activo']

class MovimientoWIPSerializer(serializers.ModelSerializer):
    id_producto = serializers.CharField(write_only=True)
    producto_id = serializers.CharField(source='producto.id_producto', read_only=True)
    descripcion_referencia = serializers.CharField(source='producto.descripcion_referencia', read_only=True)
    ufe_calculada = serializers.DecimalField(max_digits=15, decimal_places=3, read_only=True)
    movimiento_almacen = serializers.DecimalField(max_digits=15, decimal_places=3, read_only=True)
    costo_total_bs = serializers.DecimalField(max_digits=20, decimal_places=4, read_only=True, allow_null=True)
    tipo_movimiento = serializers.ChoiceField(choices=MovimientoWIP.TipoMovimiento.choices)
    class Meta:
        model = MovimientoWIP
        fields = ['id','fecha','tipo_movimiento','id_producto','producto_id','descripcion_referencia','detalle_producto','cantidad_kg','ufe','scrap_kg','area_origen','area_destino','area_posterior','entregado_por','recibido_por','referencia_ht','observaciones','costo_bs_kg','ufe_calculada','movimiento_almacen','costo_total_bs','creado_en']
        read_only_fields = ['id','creado_en']
    def validate(self, attrs):
        id_producto = attrs.pop('id_producto', None)
        if not id_producto or not str(id_producto).strip():
            raise serializers.ValidationError({'id_producto':'El ID del producto es obligatorio.'})
        try:
            producto = OrdenProducto.objects.get(id_producto=str(id_producto).strip(), activo=True)
        except OrdenProducto.DoesNotExist:
            raise serializers.ValidationError({'id_producto':'No existe un producto/trabajo activo con ese ID. Importa o registra el ID antes de continuar.'})
        attrs['producto'] = producto
        if attrs.get('scrap_kg', 0) > attrs.get('cantidad_kg', 0) and attrs.get('cantidad_kg', 0) > 0:
            # Scrap may reflect a separate production loss, so do not reject; this warning-worthy case remains allowed.
            pass
        return attrs
