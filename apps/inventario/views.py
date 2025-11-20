from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import models
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from .models import Categoria, Producto, MovimientoInventario
from .serializers import (
    CategoriaSerializer,
    ProductoSerializer,
    ProductoListSerializer,
    MovimientoInventarioSerializer,
    MovimientoInventarioCreateSerializer  # ✅ AGREGADO
)


class CategoriaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar categorías de productos
    """
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nombre', 'descripcion']
    ordering_fields = ['nombre', 'fecha_creacion']
    ordering = ['nombre']


class ProductoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar productos
    """
    queryset = Producto.objects.select_related('categoria').filter(activo=True)
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['categoria', 'activo']
    search_fields = ['nombre', 'codigo', 'descripcion']
    ordering_fields = ['nombre', 'codigo', 'precio_venta', 'stock', 'fecha_creacion']
    ordering = ['-fecha_creacion']

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductoListSerializer
        return ProductoSerializer

    @action(detail=False, methods=['get'])
    def stock_bajo(self, request):
        """
        Retorna productos con stock bajo (stock <= stock_minimo)
        """
        productos = self.queryset.filter(stock__lte=models.F('stock_minimo'))
        serializer = self.get_serializer(productos, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def actualizar_stock(self, request, pk=None):
        """
        Actualiza el stock de un producto y registra el movimiento
        """
        producto = self.get_object()
        cantidad = request.data.get('cantidad')
        tipo_movimiento = request.data.get('tipo')  # 'entrada' o 'salida'
        
        if not cantidad or not tipo_movimiento:
            return Response(
                {'error': 'Se requiere cantidad y tipo de movimiento'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            cantidad = int(cantidad)
        except ValueError:
            return Response(
                {'error': 'La cantidad debe ser un número entero'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if tipo_movimiento not in ['entrada', 'salida']:
            return Response(
                {'error': 'El tipo debe ser "entrada" o "salida"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Actualizar stock
        stock_anterior = producto.stock
        
        if tipo_movimiento == 'entrada':
            producto.stock += cantidad
        else:  # salida
            if producto.stock < cantidad:
                return Response(
                    {'error': 'Stock insuficiente'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            producto.stock -= cantidad
        
        producto.save()
        
        # Registrar movimiento
        MovimientoInventario.objects.create(
            producto=producto,
            tipo=tipo_movimiento,
            cantidad=cantidad,
            stock_anterior=stock_anterior,
            stock_nuevo=producto.stock,
            motivo=request.data.get('motivo', 'Actualización manual'),
            usuario=request.user,
            observaciones=request.data.get('observaciones', '')
        )
        
        serializer = self.get_serializer(producto)
        return Response(serializer.data)

    def perform_destroy(self, instance):
        """
        Soft delete: marca como inactivo en lugar de eliminar
        ✅ CORREGIDO: Agregar timestamp al código para evitar duplicados
        """
        from django.utils import timezone
        # Agregar timestamp al código para permitir reutilización
        instance.codigo = f"{instance.codigo}_deleted_{int(timezone.now().timestamp())}"
        instance.activo = False
        instance.save()


class MovimientoInventarioViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar movimientos de inventario
    ✅ MEJORADO: Soporte para crear entradas con precio_unitario
    """
    queryset = MovimientoInventario.objects.select_related('producto', 'usuario').all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['producto', 'tipo', 'usuario']
    ordering_fields = ['fecha', 'cantidad']
    ordering = ['-fecha']

    def get_serializer_class(self):
        """Usar serializer diferente para crear vs listar"""
        if self.action == 'create':
            return MovimientoInventarioCreateSerializer
        return MovimientoInventarioSerializer

    def perform_create(self, serializer):
        """
        Asigna automáticamente el usuario actual al crear un movimiento
        """
        serializer.save(usuario=self.request.user)
