from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count, Avg, F, Q
from django.db.models.functions import TruncDate, TruncMonth
from datetime import datetime, timedelta
from decimal import Decimal

from apps.ventas.models import Venta, DetalleVenta
from apps.inventario.models import Producto, Categoria
from apps.facturacion.models import Factura
from .models import ReporteGenerado
from .serializers import ReporteGeneradoSerializer

class ReporteViewSet(viewsets.ViewSet):
    """
    ViewSet para generar diferentes tipos de reportes
    """
    
    @action(detail=False, methods=['get'])
    def ventas_general(self, request):
        """Reporte general de ventas"""
        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin')
        
        if not fecha_inicio or not fecha_fin:
            fecha_fin = datetime.now()
            fecha_inicio = fecha_fin - timedelta(days=30)
        else:
            fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d')
            fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d')
        
        ventas = Venta.objects.filter(
            fecha__range=[fecha_inicio, fecha_fin],
            cancelada=False
        )
        
        # Estadísticas generales
        stats = ventas.aggregate(
            total_ventas=Count('id'),
            monto_total=Sum('total'),
            ticket_promedio=Avg('total'),
            total_utilidad=Sum('detalles__utilidad')
        )
        
        # Ventas por día
        ventas_por_dia = ventas.annotate(
            dia=TruncDate('fecha')
        ).values('dia').annotate(
            total=Sum('total'),
            cantidad=Count('id')
        ).order_by('dia')
        
        # Ventas por método de pago
        por_metodo = ventas.values('metodo_pago').annotate(
            total=Sum('total'),
            cantidad=Count('id')
        )
        
        # Top vendedores
        top_vendedores = ventas.values(
            'usuario__first_name', 
            'usuario__last_name'
        ).annotate(
            total_vendido=Sum('total'),
            num_ventas=Count('id')
        ).order_by('-total_vendido')[:5]
        
        return Response({
            'periodo': {
                'inicio': fecha_inicio,
                'fin': fecha_fin
            },
            'estadisticas': stats,
            'ventas_por_dia': list(ventas_por_dia),
            'por_metodo_pago': list(por_metodo),
            'top_vendedores': list(top_vendedores)
        })
    
    @action(detail=False, methods=['get'])
    def productos_mas_vendidos(self, request):
        """Productos más vendidos"""
        dias = int(request.query_params.get('dias', 30))
        fecha_inicio = datetime.now() - timedelta(days=dias)
        
        productos = DetalleVenta.objects.filter(
            venta__fecha__gte=fecha_inicio,
            venta__cancelada=False
        ).values(
            'producto__id',
            'producto__codigo',
            'producto__nombre',
            'producto__categoria__nombre'
        ).annotate(
            cantidad_vendida=Sum('cantidad'),
            total_vendido=Sum('subtotal'),
            utilidad_total=Sum('utilidad'),
            num_ventas=Count('venta', distinct=True)
        ).order_by('-cantidad_vendida')[:20]
        
        return Response(list(productos))
    
    @action(detail=False, methods=['get'])
    def inventario_actual(self, request):
        """Estado actual del inventario"""
        
        # Productos con stock bajo
        stock_bajo = Producto.objects.filter(
            stock__lte=F('stock_minimo'),
            activo=True
        ).values(
            'id', 'codigo', 'nombre', 'stock', 'stock_minimo'
        )
        
        # Productos sin stock
        sin_stock = Producto.objects.filter(
            stock=0,
            activo=True
        ).count()
        
        # Valor total del inventario
        valor_inventario = Producto.objects.filter(activo=True).aggregate(
            valor_costo=Sum(F('stock') * F('precio_costo')),
            valor_venta=Sum(F('stock') * F('precio_venta'))
        )
        
        # Productos por categoría
        por_categoria = Categoria.objects.annotate(
            total_productos=Count('productos'),
            total_stock=Sum('productos__stock'),
            valor_total=Sum(F('productos__stock') * F('productos__precio_venta'))
        ).values('nombre', 'total_productos', 'total_stock', 'valor_total')
        
        return Response({
            'resumen': {
                'productos_stock_bajo': stock_bajo.count(),
                'productos_sin_stock': sin_stock,
                'valor_inventario_costo': valor_inventario['valor_costo'] or 0,
                'valor_inventario_venta': valor_inventario['valor_venta'] or 0,
            },
            'stock_bajo': list(stock_bajo),
            'por_categoria': list(por_categoria)
        })
    
    @action(detail=False, methods=['get'])
    def analisis_financiero(self, request):
        """Análisis financiero del negocio"""
        meses = int(request.query_params.get('meses', 6))
        fecha_inicio = datetime.now() - timedelta(days=meses*30)
        
        # Ventas por mes
        ventas_mensuales = Venta.objects.filter(
            fecha__gte=fecha_inicio,
            cancelada=False
        ).annotate(
            mes=TruncMonth('fecha')
        ).values('mes').annotate(
            ingresos=Sum('total'),
            num_ventas=Count('id'),
            ticket_promedio=Avg('total')
        ).order_by('mes')
        
        # Utilidades por mes
        utilidades = DetalleVenta.objects.filter(
            venta__fecha__gte=fecha_inicio,
            venta__cancelada=False
        ).annotate(
            mes=TruncMonth('venta__fecha')
        ).values('mes').annotate(
            utilidad_total=Sum('utilidad')
        ).order_by('mes')
        
        # Facturación
        facturas_stats = Factura.objects.filter(
            fecha_creacion__gte=fecha_inicio,
            status='timbrada'
        ).aggregate(
            total_facturado=Sum('total'),
            num_facturas=Count('id')
        )
        
        return Response({
            'ventas_mensuales': list(ventas_mensuales),
            'utilidades_mensuales': list(utilidades),
            'facturacion': facturas_stats
        })
    
    @action(detail=False, methods=['get'])
    def rendimiento_categorias(self, request):
        """Análisis de rendimiento por categoría"""
        dias = int(request.query_params.get('dias', 30))
        fecha_inicio = datetime.now() - timedelta(days=dias)
        
        categorias = Categoria.objects.annotate(
            ventas_total=Sum(
                'productos__detalleventa__subtotal',
                filter=Q(
                    productos__detalleventa__venta__fecha__gte=fecha_inicio,
                    productos__detalleventa__venta__cancelada=False
                )
            ),
            cantidad_vendida=Sum(
                'productos__detalleventa__cantidad',
                filter=Q(
                    productos__detalleventa__venta__fecha__gte=fecha_inicio,
                    productos__detalleventa__venta__cancelada=False
                )
            ),
            utilidad_total=Sum(
                'productos__detalleventa__utilidad',
                filter=Q(
                    productos__detalleventa__venta__fecha__gte=fecha_inicio,
                    productos__detalleventa__venta__cancelada=False
                )
            )
        ).values(
            'nombre', 'ventas_total', 'cantidad_vendida', 'utilidad_total'
        ).order_by('-ventas_total')
        
        return Response(list(categorias))
    
    @action(detail=False, methods=['get'])
    def dashboard_metricas(self, request):
        """Métricas para el dashboard principal"""
        hoy = datetime.now().date()
        inicio_mes = hoy.replace(day=1)
        
        # Ventas de hoy
        ventas_hoy = Venta.objects.filter(
            fecha__date=hoy,
            cancelada=False
        ).aggregate(
            total=Sum('total'),
            cantidad=Count('id')
        )
        
        # Ventas del mes
        ventas_mes = Venta.objects.filter(
            fecha__date__gte=inicio_mes,
            cancelada=False
        ).aggregate(
            total=Sum('total'),
            cantidad=Count('id'),
            utilidad=Sum('detalles__utilidad')
        )
        
        # Productos con stock bajo
        productos_stock_bajo = Producto.objects.filter(
            stock__lte=F('stock_minimo'),
            activo=True
        ).count()
        
        # Productos activos
        total_productos = Producto.objects.filter(activo=True).count()
        
        return Response({
            'hoy': {
                'ventas': ventas_hoy['total'] or 0,
                'num_ventas': ventas_hoy['cantidad'] or 0
            },
            'mes_actual': {
                'ventas': ventas_mes['total'] or 0,
                'num_ventas': ventas_mes['cantidad'] or 0,
                'utilidad': ventas_mes['utilidad'] or 0
            },
            'inventario': {
                'total_productos': total_productos,
                'stock_bajo': productos_stock_bajo
            }
        })

class ReporteGeneradoViewSet(viewsets.ModelViewSet):
    queryset = ReporteGenerado.objects.all()
    serializer_class = ReporteGeneradoSerializer
    
    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)