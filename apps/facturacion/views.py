from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.conf import settings
from .models import Factura, ConceptoFactura
from .serializers import (
    FacturaSerializer, FacturaListSerializer, FacturaCreateSerializer,
    ConceptoFacturaSerializer
)
import requests
from datetime import datetime

class FacturaViewSet(viewsets.ModelViewSet):
    queryset = Factura.objects.prefetch_related('conceptos').all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'serie']
    search_fields = ['folio_fiscal', 'cliente_nombre', 'cliente_rfc']
    ordering_fields = ['fecha_creacion', 'total']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return FacturaCreateSerializer
        elif self.action == 'list':
            return FacturaListSerializer
        return FacturaSerializer
    
    @action(detail=True, methods=['post'])
    def timbrar(self, request, pk=None):
        """Timbrar factura usando Facturapi"""
        factura = self.get_object()
        
        if factura.status == 'timbrada':
            return Response(
                {'error': 'La factura ya está timbrada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not settings.FACTURAPI_SECRET_KEY:
            return Response(
                {'error': 'Facturapi no está configurado'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Preparar datos para Facturapi
        items = []
        for concepto in factura.conceptos.all():
            items.append({
                "quantity": float(concepto.cantidad),
                "product": {
                    "description": concepto.descripcion,
                    "product_key": concepto.clave_prod_serv,
                    "price": float(concepto.valor_unitario),
                    "unit_key": concepto.clave_unidad,
                    "unit_name": concepto.unidad,
                }
            })
        
        data = {
            "customer": {
                "legal_name": factura.cliente_nombre,
                "tax_id": factura.cliente_rfc,
                "email": factura.cliente_email,
                "address": {
                    "zip": factura.cliente_codigo_postal
                }
            },
            "items": items,
            "use": factura.uso_cfdi,
            "payment_form": "01",  # Efectivo
        }
        
        try:
            # Llamar a Facturapi
            response = requests.post(
                f"{settings.FACTURAPI_BASE_URL}/invoices",
                json=data,
                auth=(settings.FACTURAPI_SECRET_KEY, '')
            )
            
            if response.status_code == 201:
                factura_data = response.json()
                
                # Actualizar factura
                factura.status = 'timbrada'
                factura.folio_fiscal = factura_data.get('uuid')
                factura.fecha_timbrado = datetime.now()
                factura.xml_url = factura_data.get('xml_url')
                factura.pdf_url = factura_data.get('pdf_url')
                factura.facturapi_id = factura_data.get('id')
                factura.facturapi_response = factura_data
                factura.save()
                
                return Response({
                    'status': 'Factura timbrada exitosamente',
                    'folio_fiscal': factura.folio_fiscal,
                    'xml_url': factura.xml_url,
                    'pdf_url': factura.pdf_url
                })
            else:
                return Response(
                    {'error': 'Error al timbrar', 'details': response.json()},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        except Exception as e:
            return Response(
                {'error': f'Error de conexión: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """Cancelar factura timbrada"""
        factura = self.get_object()
        
        if factura.status != 'timbrada':
            return Response(
                {'error': 'Solo se pueden cancelar facturas timbradas'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        motivo = request.data.get('motivo', '')
        
        if not motivo:
            return Response(
                {'error': 'El motivo de cancelación es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Cancelar en Facturapi
            if factura.facturapi_id and settings.FACTURAPI_SECRET_KEY:
                response = requests.delete(
                    f"{settings.FACTURAPI_BASE_URL}/invoices/{factura.facturapi_id}",
                    auth=(settings.FACTURAPI_SECRET_KEY, '')
                )
                
                if response.status_code not in [200, 204]:
                    return Response(
                        {'error': 'Error al cancelar en Facturapi'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Actualizar factura
            factura.status = 'cancelada'
            factura.fecha_cancelacion = datetime.now()
            factura.motivo_cancelacion = motivo
            factura.save()
            
            return Response({'status': 'Factura cancelada exitosamente'})
        
        except Exception as e:
            return Response(
                {'error': f'Error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def descargar_xml(self, request, pk=None):
        """Descargar XML de la factura"""
        factura = self.get_object()
        
        if not factura.xml_url:
            return Response(
                {'error': 'XML no disponible'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response({'xml_url': factura.xml_url})
    
    @action(detail=True, methods=['get'])
    def descargar_pdf(self, request, pk=None):
        """Descargar PDF de la factura"""
        factura = self.get_object()
        
        if not factura.pdf_url:
            return Response(
                {'error': 'PDF no disponible'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response({'pdf_url': factura.pdf_url})
    
    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """Estadísticas de facturación"""
        from django.db.models import Sum, Count
        
        stats = {
            'total_facturas': self.queryset.count(),
            'timbradas': self.queryset.filter(status='timbrada').count(),
            'canceladas': self.queryset.filter(status='cancelada').count(),
            'borradores': self.queryset.filter(status='borrador').count(),
            'monto_total': self.queryset.filter(status='timbrada').aggregate(
                total=Sum('total')
            )['total'] or 0,
        }
        
        return Response(stats)