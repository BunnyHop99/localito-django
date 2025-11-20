from django.contrib import admin
from .models import Categoria, Producto, MovimientoInventario

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activo', 'fecha_creacion')
    list_filter = ('activo',)
    search_fields = ('nombre',)

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'categoria', 'stock', 'stock_minimo', 'precio_venta', 'activo')
    list_filter = ('categoria', 'activo')
    search_fields = ('codigo', 'nombre')
    list_editable = ('stock', 'precio_venta')

@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = ('producto', 'tipo', 'cantidad', 'stock_anterior', 'stock_nuevo', 'usuario', 'fecha')
    list_filter = ('tipo', 'fecha')
    search_fields = ('producto__nombre', 'motivo')
    date_hierarchy = 'fecha'