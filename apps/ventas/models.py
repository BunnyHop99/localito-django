from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from apps.inventario.models import Producto
from apps.usuarios.models import Usuario

class Venta(models.Model):
    METODOS_PAGO = (
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta'),
        ('transferencia', 'Transferencia'),
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
        ]
    
    def __str__(self):
        return f"Venta {self.folio} - ${self.total}"
    
    def calcular_totales(self):
        detalles = self.detalles.all()
        self.subtotal = sum(d.subtotal for d in detalles)
        self.iva = self.subtotal * Decimal('0.16')
        self.total = self.subtotal + self.iva
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