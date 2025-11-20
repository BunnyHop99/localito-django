from django.contrib import admin
from .models import Venta, DetalleVenta

class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 0
    readonly_fields = ('subtotal', 'utilidad')

@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ('folio', 'fecha', 'cliente_nombre', 'total', 'metodo_pago', 'usuario', 'cancelada')
    list_filter = ('metodo_pago', 'cancelada', 'fecha')
    search_fields = ('folio', 'cliente_nombre')
    date_hierarchy = 'fecha'
    inlines = [DetalleVentaInline]
    readonly_fields = ('folio', 'subtotal', 'iva', 'total')