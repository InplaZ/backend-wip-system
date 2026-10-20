from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator

class OrdenProducto(models.Model):
    """Identificador de trabajo. El detalle puede cambiar entre etapas del proceso."""
    id_producto = models.CharField(max_length=60, unique=True, db_index=True)
    descripcion_referencia = models.CharField(max_length=255, blank=True)
    cot_ref = models.CharField(max_length=120, blank=True)
    cantidad_solicitada_kg = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True, validators=[MinValueValidator(0)])
    cantidad_solicitada_unidades = models.PositiveIntegerField(null=True, blank=True)
    fecha_entrega = models.DateField(null=True, blank=True)
    valor_pedido_bs = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    codigo_producto_homologado = models.CharField(max_length=120, blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['id_producto']
        verbose_name = 'ID de producto/trabajo'
        verbose_name_plural = 'IDs de producto/trabajo'
    def __str__(self):
        return f'{self.id_producto} — {self.descripcion_referencia}'

    def save(self, *args, **kwargs):
        if not self.id_producto:
            self.id_producto = f'{self.pk:04d}' if self.pk else 'PENDING'
            super().save(*args, **kwargs)
            if self.id_producto == 'PENDING':
                self.id_producto = f'{self.pk:04d}'
                type(self).objects.filter(pk=self.pk).update(id_producto=self.id_producto)
            return
        super().save(*args, **kwargs)

class MovimientoWIP(models.Model):
    class TipoMovimiento(models.TextChoices):
        INGRESO = 'INGRESO', 'Ingreso'
        SALIDA = 'SALIDA', 'Salida'
        TRASPASO = 'TRASPASO', 'Traspaso'
    class Criticidad(models.TextChoices):
        NORMAL = 'NORMAL', 'Normal'
        CRITICO = 'CRÍTICO', 'Crítico'
    fecha = models.DateField(db_index=True)
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    tipo_movimiento = models.CharField(max_length=12, choices=TipoMovimiento.choices, db_index=True)
    criticidad = models.CharField(max_length=12, choices=Criticidad.choices, default=Criticidad.NORMAL, db_index=True)
    producto = models.ForeignKey(OrdenProducto, on_delete=models.PROTECT, related_name='movimientos')
    detalle_producto = models.CharField(max_length=255)
    registrado_por = models.CharField(max_length=150, blank=True, default='')
    registrado_por_usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='movimientos_wip_registrados')
    cantidad_kg = models.DecimalField(max_digits=14, decimal_places=3, validators=[MinValueValidator(0)])
    ufe = models.DecimalField(max_digits=14, decimal_places=3, validators=[MinValueValidator(0)])
    scrap_kg = models.DecimalField(max_digits=14, decimal_places=3, default=0, validators=[MinValueValidator(0)])
    area_origen = models.CharField(max_length=80)
    area_destino = models.CharField(max_length=80)
    area_posterior = models.CharField(max_length=80, blank=True)
    entregado_por = models.CharField(max_length=120)
    recibido_por = models.CharField(max_length=120)
    usuario_destino = models.CharField(max_length=150, blank=True)
    destinatario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='movimientos_wip_recibidos')
    estado_recepcion = models.CharField(max_length=20, default='PENDIENTE', choices=[('PENDIENTE','Pendiente'),('ACEPTADO','Aceptado'),('OBSERVADO','Observado'),('NO_CONFORME','No conforme (legado)'),('RECHAZADO','Rechazado')])
    respuesta_recepcion = models.TextField(blank=True)
    respondido_por_usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='respuestas_wip_realizadas')
    fecha_respuesta = models.DateTimeField(null=True, blank=True)
    idempotency_key = models.UUIDField(null=True, blank=True, unique=True, editable=False)
    referencia_ht = models.CharField(max_length=120, blank=True)
    codigo_talonario = models.CharField(max_length=120, blank=True)
    codigo_producto_homologado = models.CharField(max_length=120, blank=True)
    cot_ref = models.CharField(max_length=120, blank=True)
    observaciones = models.TextField(blank=True)
    evidencias = models.JSONField(default=list, blank=True)
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

class RespuestaMovimiento(models.Model):
    class Accion(models.TextChoices):
        REGISTRADO = 'REGISTRADO', 'Registrado'
        ACEPTADO = 'ACEPTADO', 'Aceptado'
        OBSERVADO = 'OBSERVADO', 'Observado'
        RECHAZADO = 'RECHAZADO', 'Rechazado'
        REABIERTO = 'REABIERTO', 'Reabierto'
    movimiento = models.ForeignKey(MovimientoWIP, on_delete=models.CASCADE, related_name='historial_respuestas')
    accion = models.CharField(max_length=20, choices=Accion.choices)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='historial_respuestas_wip')
    nombre_usuario = models.CharField(max_length=150)
    comentario = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['creado_en', 'id']
        indexes = [models.Index(fields=['movimiento', 'creado_en'], name='wip_resp_movimie_3fc2f0_idx')]

class NotificacionWIP(models.Model):
    class Tipo(models.TextChoices):
        MOVIMIENTO_RECIBIDO = 'MOVIMIENTO_RECIBIDO', 'Movimiento recibido'
        RESPUESTA_MOVIMIENTO = 'RESPUESTA_MOVIMIENTO', 'Respuesta del movimiento'
        MOVIMIENTO_REABIERTO = 'MOVIMIENTO_REABIERTO', 'Movimiento reabierto'
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notificaciones_wip')
    movimiento = models.ForeignKey(MovimientoWIP, on_delete=models.CASCADE, related_name='notificaciones')
    respuesta = models.ForeignKey(RespuestaMovimiento, null=True, blank=True, on_delete=models.SET_NULL, related_name='notificaciones')
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    titulo = models.CharField(max_length=180)
    mensaje = models.TextField()
    creado_en = models.DateTimeField(auto_now_add=True)
    fecha_lectura = models.DateTimeField(null=True, blank=True)
    class Meta:
        ordering = ['-creado_en', '-id']
        indexes = [models.Index(fields=['usuario', 'fecha_lectura', '-creado_en'], name='wip_notif_user_read_idx')]
