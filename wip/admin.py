from django.contrib import admin
from .models import OrdenProducto, MovimientoWIP
@admin.register(OrdenProducto)
class OrdenProductoAdmin(admin.ModelAdmin):
    list_display = ('id_producto','descripcion_referencia','activo')
    search_fields = ('id_producto','descripcion_referencia')
@admin.register(MovimientoWIP)
class MovimientoWIPAdmin(admin.ModelAdmin):
    list_display = ('fecha','tipo_movimiento','producto','detalle_producto','cantidad_kg','area_origen','area_destino')
    list_filter = ('fecha','tipo_movimiento','area_origen','area_destino')
    search_fields = ('producto__id_producto','detalle_producto','referencia_ht')
