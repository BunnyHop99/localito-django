from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from apps.inventario.models import Producto
from apps.usuarios.models import Usuario
from django.utils import timezone
from datetime import timedelta

class Venta(models.Model):
    METODOS_PAGO = (
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta'),
        ('transferencia', 'Transferencia'),
        ('credito', 'Crédito'),
    )
    
    DIAS_CREDITO = (
        (15, '15 días'),
        (30, '30 días'),
    )
    
    ESTADO_CREDITO = (
        ('pendiente', 'Pendiente'),
        ('pagado', 'Pagado'),
        ('vencido', 'Vencido'),
    )
    
    folio = models.CharField(max_length=50, unique=True, db_index=True)
    fecha = models.DateTimeField(auto_now_add=True)
    
    # Cliente
    cliente_nombre = models.CharField(max_length=200, default='Público General')
    cliente_rfc = models.CharField(max_length=13, blank=True, null=True)
    
    # Totales
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    iva = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Pago
    metodo_pago = models.CharField(max_length=20, choices=METODOS_PAGO)
    
    # Crédito
    dias_credito = models.IntegerField(choices=DIAS_CREDITO, null=True, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    estado_credito = models.CharField(max_length=20, choices=ESTADO_CREDITO, null=True, blank=True)
    fecha_pago = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name='ventas')
    observaciones = models.TextField(blank=True)
    cancelada = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'ventas'
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['folio']),
            models.Index(fields=['fecha']),
            models.Index(fields=['estado_credito']),
            models.Index(fields=['fecha_vencimiento']),
        ]
    
    def __str__(self):
        return f"Venta {self.folio} - ${self.total}"
    
    def save(self, *args, **kwargs):
        # Guardar primero para que se genere la fecha
        es_nuevo = self.pk is None
        super().save(*args, **kwargs)
        
        # Calcular fecha de vencimiento si es crédito y es una nueva venta
        if es_nuevo and self.metodo_pago == 'credito' and self.dias_credito and not self.fecha_vencimiento:
            self.fecha_vencimiento = (self.fecha + timedelta(days=self.dias_credito)).date()
            self.estado_credito = 'pendiente'
            # Guardar de nuevo solo si se modificó algo
            super().save(update_fields=['fecha_vencimiento', 'estado_credito'])
    
    def calcular_totales(self):
        detalles = self.detalles.all()
        self.subtotal = sum(d.subtotal for d in detalles)
        self.iva = self.subtotal * Decimal('0.16')
        self.total = self.subtotal + self.iva
        self.save()
    
    def dias_para_vencimiento(self):
        """Calcula los días que faltan para el vencimiento"""
        if self.fecha_vencimiento and self.estado_credito == 'pendiente':
            dias = (self.fecha_vencimiento - timezone.now().date()).days
            return dias
        return None
    
    def esta_por_vencer(self):
        """Verifica si el crédito está por vencer (2 días o menos)"""
        dias = self.dias_para_vencimiento()
        return dias is not None and 0 <= dias <= 2
    
    def actualizar_estado_credito(self):
        """Actualiza el estado del crédito automáticamente"""
        if self.metodo_pago == 'credito' and self.estado_credito == 'pendiente':
            if timezone.now().date() > self.fecha_vencimiento:
                self.estado_credito = 'vencido'
                self.save()

class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    
    cantidad = models.IntegerField(validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Para cálculo de utilidad
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    utilidad = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        db_table = 'detalles_venta'
        verbose_name = 'Detalle de Venta'
        verbose_name_plural = 'Detalles de Venta'
    
    def save(self, *args, **kwargs):
        self.subtotal = self.cantidad * self.precio_unitario
        self.utilidad = (self.precio_unitario - self.costo_unitario) * self.cantidad
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.producto.nombre} x {self.cantidad}"