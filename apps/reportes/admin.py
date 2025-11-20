from django.contrib import admin
from .models import ReporteGenerado

@admin.register(ReporteGenerado)
class ReporteGeneradoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'fecha_inicio', 'fecha_fin', 'formato', 'usuario', 'fecha_generacion')
    list_filter = ('tipo', 'formato', 'fecha_generacion')
    search_fields = ('nombre', 'descripcion')
    date_hierarchy = 'fecha_generacion'
    readonly_fields = ('fecha_generacion',)