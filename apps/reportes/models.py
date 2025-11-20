# Esta app no necesita modelos propios, usa los de otras apps
from django.db import models

# Opcionalmente puedes crear modelos para guardar reportes generados
class ReporteGenerado(models.Model):
    TIPOS = (
        ('ventas', 'Ventas'),
        ('inventario', 'Inventario'),
        ('financiero', 'Financiero'),
        ('productos', 'Productos'),
    )
    
    nombre = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    descripcion = models.TextField(blank=True)
    
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    
    archivo = models.FileField(upload_to='reportes/')
    formato = models.CharField(max_length=10)  # PDF, XLSX, CSV
    
    usuario = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True)
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'reportes_generados'
        verbose_name = 'Reporte Generado'
        verbose_name_plural = 'Reportes Generados'
        ordering = ['-fecha_generacion']
    
    def __str__(self):
        return f"{self.nombre} - {self.fecha_generacion.strftime('%Y-%m-%d')}"