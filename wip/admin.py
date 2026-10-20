from django.contrib import admin
from .models import OrdenProducto, MovimientoWIP, RespuestaMovimiento, NotificacionWIP
@admin.register(OrdenProducto)
class OrdenProductoAdmin(admin.ModelAdmin):
    list_display = ('id_producto','descripcion_referencia','activo')
    search_fields = ('id_producto','descripcion_referencia')
@admin.register(MovimientoWIP)
class MovimientoWIPAdmin(admin.ModelAdmin):
    list_display = ('fecha','tipo_movimiento','producto','detalle_producto','cantidad_kg','area_origen','area_destino')
    list_filter = ('fecha','tipo_movimiento','area_origen','area_destino')
    search_fields = ('producto__id_producto','detalle_producto','referencia_ht')
    readonly_fields = ('registrado_por_usuario','destinatario','respondido_por_usuario','fecha_respuesta','idempotency_key')

@admin.register(RespuestaMovimiento)
class RespuestaMovimientoAdmin(admin.ModelAdmin):
    list_display=('movimiento','accion','nombre_usuario','creado_en')
    list_filter=('accion','creado_en')
    search_fields=('movimiento__producto__id_producto','nombre_usuario','comentario')
    readonly_fields=('movimiento','accion','usuario','nombre_usuario','comentario','creado_en')

@admin.register(NotificacionWIP)
class NotificacionWIPAdmin(admin.ModelAdmin):
    list_display=('usuario','tipo','movimiento','creado_en','fecha_lectura')
    list_filter=('tipo','fecha_lectura','creado_en')
    search_fields=('usuario__username','titulo','mensaje','movimiento__producto__id_producto')
    readonly_fields=('usuario','movimiento','respuesta','tipo','titulo','mensaje','creado_en','fecha_lectura')
