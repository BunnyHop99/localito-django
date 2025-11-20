from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Count, F
from datetime import datetime, timedelta
from .models import Venta, DetalleVenta
from .serializers import (
    VentaSerializer, VentaListSerializer, VentaCreateSerializer,
    DetalleVentaSerializer
)

class VentaViewSet(viewsets.ModelViewSet):
    queryset = Venta.objects.select_related('usuario').prefetch_related('detalles').all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['metodo_pago', 'cancelada']
    search_fields = ['folio', 'cliente_nombre']
    ordering_fields = ['fecha', 'total']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return VentaCreateSerializer
        elif self.action == 'list':
            return VentaListSerializer
        return VentaSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
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
        
        # Regresar stock
        for detalle in venta.detalles.all():
            producto = detalle.producto
            producto.stock += detalle.cantidad
            producto.save()
        
        venta.cancelada = True
        venta.save()
        
        return Response({'status': 'Venta cancelada correctamente'})
    
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