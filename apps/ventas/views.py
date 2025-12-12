from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Count, F, Q
from datetime import datetime, timedelta
from django.utils import timezone
from .models import Venta, DetalleVenta
from .serializers import (
    VentaSerializer, VentaListSerializer, VentaCreateSerializer,
    DetalleVentaSerializer, MarcarPagadoSerializer
)

class VentaViewSet(viewsets.ModelViewSet):
    queryset = Venta.objects.select_related('usuario').prefetch_related('detalles').all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['metodo_pago', 'cancelada', 'estado_credito']
    search_fields = ['folio', 'cliente_nombre']
    ordering_fields = ['fecha', 'total']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return VentaCreateSerializer
        elif self.action == 'list':
            return VentaListSerializer
        elif self.action == 'marcar_pagado':
            return MarcarPagadoSerializer
        return VentaSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Actualizar estados de crédito vencidos
        for venta in queryset.filter(metodo_pago='credito', estado_credito='pendiente'):
            venta.actualizar_estado_credito()
        
        # Filtrar por rango de fechas
        fecha_inicio = self.request.query_params.get('fecha_inicio')
        fecha_fin = self.request.query_params.get('fecha_fin')
        
        if fecha_inicio:
            queryset = queryset.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha__lte=fecha_fin)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        venta = self.get_object()
        
        if venta.cancelada:
            return Response(
                {'error': 'La venta ya está cancelada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # No permitir cancelar ventas a crédito pagadas
        if venta.metodo_pago == 'credito' and venta.estado_credito == 'pagado':
            return Response(
                {'error': 'No se puede cancelar una venta a crédito ya pagada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Regresar stock
        for detalle in venta.detalles.all():
            producto = detalle.producto
            producto.stock += detalle.cantidad
            producto.save()
        
        venta.cancelada = True
        venta.save()
        
        return Response({'status': 'Venta cancelada correctamente'})
    
    @action(detail=True, methods=['post'])
    def marcar_pagado(self, request, pk=None):
        """Marcar una venta a crédito como pagada"""
        venta = self.get_object()
        
        if venta.metodo_pago != 'credito':
            return Response(
                {'error': 'Esta venta no es a crédito'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if venta.estado_credito == 'pagado':
            return Response(
                {'error': 'Esta venta ya está marcada como pagada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        venta.estado_credito = 'pagado'
        venta.fecha_pago = timezone.now()
        venta.save()
        
        serializer = self.get_serializer(venta)
        return Response({
            'status': 'Venta marcada como pagada',
            'venta': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def estadisticas_hoy(self, request):
        hoy = datetime.now().date()
        ventas_hoy = self.queryset.filter(fecha__date=hoy, cancelada=False)
        
        return Response({
            'total_ventas': ventas_hoy.count(),
            'monto_total': ventas_hoy.aggregate(total=Sum('total'))['total'] or 0,
            'ticket_promedio': ventas_hoy.aggregate(promedio=Sum('total'))['promedio'] or 0,
        })
    
    @action(detail=False, methods=['get'])
    def ventas_por_periodo(self, request):
        dias = int(request.query_params.get('dias', 30))
        fecha_inicio = datetime.now() - timedelta(days=dias)
        
        ventas = self.queryset.filter(
            fecha__gte=fecha_inicio,
            cancelada=False
        ).values('fecha__date').annotate(
            total=Sum('total'),
            cantidad=Count('id')
        ).order_by('fecha__date')
        
        return Response(ventas)
    
    @action(detail=False, methods=['get'])
    def creditos_pendientes(self, request):
        """Obtener ventas a crédito pendientes"""
        creditos = self.queryset.filter(
            metodo_pago='credito',
            estado_credito='pendiente',
            cancelada=False
        ).select_related('usuario')
        
        serializer = VentaListSerializer(creditos, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def creditos_por_vencer(self, request):
        """Obtener ventas a crédito que vencen en 2 días o menos"""
        hoy = timezone.now().date()
        fecha_limite = hoy + timedelta(days=2)
        
        creditos = self.queryset.filter(
            metodo_pago='credito',
            estado_credito='pendiente',
            fecha_vencimiento__lte=fecha_limite,
            fecha_vencimiento__gte=hoy,
            cancelada=False
        ).select_related('usuario')
        
        serializer = VentaListSerializer(creditos, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def creditos_vencidos(self, request):
        """Obtener ventas a crédito vencidas"""
        creditos = self.queryset.filter(
            metodo_pago='credito',
            estado_credito='vencido',
            cancelada=False
        ).select_related('usuario')
        
        serializer = VentaListSerializer(creditos, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def notificaciones(self, request):
        """Obtener todas las notificaciones (stock bajo + créditos por vencer)"""
        from apps.inventario.models import Producto
        
        # Productos con stock bajo
        productos_bajo_stock = Producto.objects.filter(
            stock__lte=F('stock_minimo'),
            activo=True
        ).count()
        
        # Créditos por vencer (2 días o menos)
        hoy = timezone.now().date()
        fecha_limite = hoy + timedelta(days=2)
        
        creditos_por_vencer = self.queryset.filter(
            metodo_pago='credito',
            estado_credito='pendiente',
            fecha_vencimiento__lte=fecha_limite,
            fecha_vencimiento__gte=hoy,
            cancelada=False
        )
        
        # Créditos vencidos
        creditos_vencidos = self.queryset.filter(
            metodo_pago='credito',
            estado_credito='vencido',
            cancelada=False
        )
        
        notificaciones = []
        
        # Agregar notificación de stock bajo
        if productos_bajo_stock > 0:
            notificaciones.append({
                'tipo': 'stock_bajo',
                'titulo': 'Productos con stock bajo',
                'mensaje': f'Hay {productos_bajo_stock} producto(s) que requieren reabastecimiento',
                'cantidad': productos_bajo_stock,
                'prioridad': 'media',
                'icono': 'package'
            })
        
        # Agregar notificaciones de créditos por vencer
        for venta in creditos_por_vencer:
            dias = venta.dias_para_vencimiento()
            notificaciones.append({
                'tipo': 'credito_por_vencer',
                'titulo': f'Crédito por vencer - {venta.folio}',
                'mensaje': f'{venta.cliente_nombre} - ${venta.total} - Vence en {dias} día(s)',
                'venta_id': venta.id,
                'folio': venta.folio,
                'dias_restantes': dias,
                'monto': float(venta.total),
                'cliente': venta.cliente_nombre,
                'prioridad': 'alta' if dias == 0 else 'media',
                'icono': 'alert-circle'
            })
        
        # Agregar notificaciones de créditos vencidos
        for venta in creditos_vencidos:
            dias_vencido = abs(venta.dias_para_vencimiento())
            notificaciones.append({
                'tipo': 'credito_vencido',
                'titulo': f'Crédito vencido - {venta.folio}',
                'mensaje': f'{venta.cliente_nombre} - ${venta.total} - Vencido hace {dias_vencido} día(s)',
                'venta_id': venta.id,
                'folio': venta.folio,
                'dias_vencido': dias_vencido,
                'monto': float(venta.total),
                'cliente': venta.cliente_nombre,
                'prioridad': 'urgente',
                'icono': 'x-circle'
            })
        
        return Response({
            'total': len(notificaciones),
            'notificaciones': notificaciones
        })