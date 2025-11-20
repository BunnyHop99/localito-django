from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'categorias'
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre

class Producto(models.Model):
    codigo = models.CharField(max_length=50, unique=True, db_index=True)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='productos')
    
    # Inventario
    stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    stock_minimo = models.IntegerField(default=10, validators=[MinValueValidator(0)])
    
    # Precios
    precio_costo = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    
    # Metadata
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True)
    codigo_barras = models.CharField(max_length=50, blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    ultima_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'productos'
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['nombre']),
            models.Index(fields=['categoria']),
        ]
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
    
    @property
    def stock_bajo(self):
        return self.stock <= self.stock_minimo
    
    @property
    def margen_utilidad(self):
        if self.precio_costo > 0:
            return ((self.precio_venta - self.precio_costo) / self.precio_costo) * 100
        return 0

class MovimientoInventario(models.Model):
    TIPOS = (
        ('entrada', 'Entrada'),
        ('salida', 'Salida'),
        ('ajuste', 'Ajuste'),
    )
    
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='movimientos')
    tipo = models.CharField(max_length=20, choices=TIPOS)
    cantidad = models.IntegerField(validators=[MinValueValidator(1)])
    stock_anterior = models.IntegerField()
    stock_nuevo = models.IntegerField()
    
    motivo = models.CharField(max_length=200)
    observaciones = models.TextField(blank=True)
    
    usuario = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True)
    fecha = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'movimientos_inventario'
        verbose_name = 'Movimiento de Inventario'
        verbose_name_plural = 'Movimientos de Inventario'
        ordering = ['-fecha']
    
    def __str__(self):
        return f"{self.tipo} - {self.producto.nombre} ({self.cantidad})"