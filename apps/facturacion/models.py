from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from apps.ventas.models import Venta
from apps.usuarios.models import Usuario

class Factura(models.Model):
    STATUS_CHOICES = (
        ('borrador', 'Borrador'),
        ('timbrada', 'Timbrada'),
        ('cancelada', 'Cancelada'),
    )
    
    USO_CFDI = (
        ('G01', 'Adquisición de mercancías'),
        ('G02', 'Devoluciones, descuentos o bonificaciones'),
        ('G03', 'Gastos en general'),
        ('I01', 'Construcciones'),
        ('I02', 'Mobilario y equipo de oficina por inversiones'),
        ('I03', 'Equipo de transporte'),
        ('I04', 'Equipo de computo y accesorios'),
        ('I05', 'Dados, troqueles, moldes, matrices y herramental'),
        ('I06', 'Comunicaciones telefónicas'),
        ('I07', 'Comunicaciones satelitales'),
        ('I08', 'Otra maquinaria y equipo'),
        ('D01', 'Honorarios médicos, dentales y gastos hospitalarios'),
        ('D02', 'Gastos médicos por incapacidad o discapacidad'),
        ('D03', 'Gastos funerales'),
        ('D04', 'Donativos'),
        ('D05', 'Intereses reales efectivamente pagados por créditos hipotecarios (casa habitación)'),
        ('D06', 'Aportaciones voluntarias al SAR'),
        ('D07', 'Primas por seguros de gastos médicos'),
        ('D08', 'Gastos de transportación escolar obligatoria'),
        ('D09', 'Depósitos en cuentas para el ahorro, primas que tengan como base planes de pensiones'),
        ('D10', 'Pagos por servicios educativos (colegiaturas)'),
        ('P01', 'Por definir'),
    )
    
    # Relaciones
    venta = models.OneToOneField(Venta, on_delete=models.PROTECT, related_name='factura', null=True, blank=True)
    
    # Información fiscal
    folio_fiscal = models.CharField(max_length=36, unique=True, db_index=True)
    serie = models.CharField(max_length=10, default='A')
    folio = models.IntegerField()
    
    # Cliente
    cliente_rfc = models.CharField(max_length=13)
    cliente_nombre = models.CharField(max_length=200)
    cliente_email = models.EmailField()
    cliente_codigo_postal = models.CharField(max_length=5)
    uso_cfdi = models.CharField(max_length=3, choices=USO_CFDI, default='P01')
    
    # Montos
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    iva = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    
    # Estado
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='borrador')
    
    # Archivos
    xml_url = models.URLField(blank=True, null=True)
    pdf_url = models.URLField(blank=True, null=True)
    xml_file = models.FileField(upload_to='facturas/xml/', blank=True, null=True)
    pdf_file = models.FileField(upload_to='facturas/pdf/', blank=True, null=True)
    
    # Timbrado
    fecha_timbrado = models.DateTimeField(null=True, blank=True)
    fecha_cancelacion = models.DateTimeField(null=True, blank=True)
    motivo_cancelacion = models.TextField(blank=True)
    
    # Metadata
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name='facturas')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    ultima_actualizacion = models.DateTimeField(auto_now=True)
    
    # Respuesta de Facturapi
    facturapi_id = models.CharField(max_length=100, blank=True, null=True)
    facturapi_response = models.JSONField(blank=True, null=True)
    
    class Meta:
        db_table = 'facturas'
        verbose_name = 'Factura'
        verbose_name_plural = 'Facturas'
        ordering = ['-fecha_creacion']
        unique_together = [['serie', 'folio']]
        indexes = [
            models.Index(fields=['folio_fiscal']),
            models.Index(fields=['cliente_rfc']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.serie}-{self.folio} - {self.cliente_nombre}"
    
    @property
    def numero_completo(self):
        return f"{self.serie}-{self.folio}"

class ConceptoFactura(models.Model):
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name='conceptos')
    
    # SAT
    clave_prod_serv = models.CharField(max_length=10, default='01010101')  # Clave SAT
    clave_unidad = models.CharField(max_length=10, default='H87')  # Pieza
    
    # Descripción
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    unidad = models.CharField(max_length=50, default='Pieza')
    descripcion = models.TextField()
    
    # Precios
    valor_unitario = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    importe = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Impuestos
    iva = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    class Meta:
        db_table = 'conceptos_factura'
        verbose_name = 'Concepto de Factura'
        verbose_name_plural = 'Conceptos de Factura'
    
    def save(self, *args, **kwargs):
        self.importe = self.cantidad * self.valor_unitario
        self.iva = self.importe * Decimal('0.16')
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.descripcion} - {self.cantidad}"