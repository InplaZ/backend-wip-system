from django.db import models
from django.core.validators import MinValueValidator

class OrdenProducto(models.Model):
    """Identificador de trabajo. El detalle puede cambiar entre etapas del proceso."""
    id_producto = models.CharField(max_length=60, unique=True, db_index=True)
    descripcion_referencia = models.CharField(max_length=255, blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['id_producto']
        verbose_name = 'ID de producto/trabajo'
        verbose_name_plural = 'IDs de producto/trabajo'
    def __str__(self):
        return f'{self.id_producto} — {self.descripcion_referencia}'

class MovimientoWIP(models.Model):
    class TipoMovimiento(models.TextChoices):
        INGRESO = 'INGRESO', 'Ingreso'
        SALIDA = 'SALIDA', 'Salida'
        TRASPASO = 'TRASPASO', 'Traspaso'
    fecha = models.DateField(db_index=True)
    tipo_movimiento = models.CharField(max_length=12, choices=TipoMovimiento.choices, db_index=True)
    producto = models.ForeignKey(OrdenProducto, on_delete=models.PROTECT, related_name='movimientos')
    detalle_producto = models.CharField(max_length=255)
    cantidad_kg = models.DecimalField(max_digits=14, decimal_places=3, validators=[MinValueValidator(0)])
    ufe = models.DecimalField(max_digits=14, decimal_places=3, validators=[MinValueValidator(0)])
    scrap_kg = models.DecimalField(max_digits=14, decimal_places=3, default=0, validators=[MinValueValidator(0)])
    area_origen = models.CharField(max_length=80)
    area_destino = models.CharField(max_length=80)
    area_posterior = models.CharField(max_length=80, blank=True)
    entregado_por = models.CharField(max_length=120)
    recibido_por = models.CharField(max_length=120)
    referencia_ht = models.CharField(max_length=120, blank=True)
    observaciones = models.TextField(blank=True)
    costo_bs_kg = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True, validators=[MinValueValidator(0)])
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['fecha', 'id']
        indexes = [models.Index(fields=['producto', 'fecha']), models.Index(fields=['fecha', 'tipo_movimiento']), models.Index(fields=['area_origen', 'fecha'])]
        verbose_name = 'Movimiento WIP'
        verbose_name_plural = 'Movimientos WIP'
    @property
    def ufe_calculada(self):
        if self.tipo_movimiento == self.TipoMovimiento.INGRESO: return self.ufe
        if self.tipo_movimiento == self.TipoMovimiento.SALIDA: return -self.ufe
        return 0
    @property
    def movimiento_almacen(self):
        if self.tipo_movimiento == self.TipoMovimiento.INGRESO: return self.cantidad_kg
        if self.tipo_movimiento == self.TipoMovimiento.SALIDA: return -self.cantidad_kg
        return 0
    @property
    def costo_total_bs(self):
        return self.movimiento_almacen * self.costo_bs_kg if self.costo_bs_kg is not None else None
    def __str__(self): return f'{self.fecha} {self.tipo_movimiento} ID {self.producto.id_producto}'
