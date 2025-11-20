from django.contrib import admin
from .models import Factura, ConceptoFactura

class ConceptoFacturaInline(admin.TabularInline):
    model = ConceptoFactura
    extra = 0
    readonly_fields = ('importe', 'iva')

@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ('numero_completo', 'folio_fiscal', 'cliente_nombre', 'total', 'status', 'fecha_creacion')
    list_filter = ('status', 'serie', 'fecha_creacion')
    search_fields = ('folio_fiscal', 'cliente_nombre', 'cliente_rfc')
    date_hierarchy = 'fecha_creacion'
    inlines = [ConceptoFacturaInline]
    readonly_fields = ('folio_fiscal', 'fecha_timbrado', 'fecha_cancelacion', 'facturapi_id')
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('venta', 'serie', 'folio', 'folio_fiscal')
        }),
        ('Cliente', {
            'fields': ('cliente_rfc', 'cliente_nombre', 'cliente_email', 
                      'cliente_codigo_postal', 'uso_cfdi')
        }),
        ('Montos', {
            'fields': ('subtotal', 'iva', 'total')
        }),
        ('Estado', {
            'fields': ('status', 'fecha_timbrado', 'fecha_cancelacion', 'motivo_cancelacion')
        }),
        ('Archivos', {
            'fields': ('xml_url', 'pdf_url', 'xml_file', 'pdf_file')
        }),
        ('Facturapi', {
            'fields': ('facturapi_id', 'facturapi_response'),
            'classes': ('collapse',)
        }),
    )