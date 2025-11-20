from rest_framework import serializers
from .models import Factura, ConceptoFactura

class ConceptoFacturaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConceptoFactura
        fields = '__all__'
        read_only_fields = ('factura', 'importe', 'iva')

class ConceptoFacturaCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConceptoFactura
        fields = ('clave_prod_serv', 'clave_unidad', 'cantidad', 'unidad', 
                 'descripcion', 'valor_unitario')

class FacturaSerializer(serializers.ModelSerializer):
    conceptos = ConceptoFacturaSerializer(many=True, read_only=True)
    usuario_nombre = serializers.CharField(source='usuario.get_full_name', read_only=True)
    numero_completo = serializers.CharField(read_only=True)
    
    class Meta:
        model = Factura
        fields = '__all__'
        read_only_fields = ('folio_fiscal', 'status', 'fecha_timbrado', 'fecha_cancelacion',
                           'xml_url', 'pdf_url', 'usuario', 'facturapi_id', 'facturapi_response')

class FacturaListSerializer(serializers.ModelSerializer):
    numero_completo = serializers.CharField(read_only=True)
    
    class Meta:
        model = Factura
        fields = ('id', 'numero_completo', 'folio_fiscal', 'cliente_nombre', 'cliente_rfc',
                 'total', 'status', 'fecha_creacion', 'fecha_timbrado')

class FacturaCreateSerializer(serializers.ModelSerializer):
    conceptos = ConceptoFacturaCreateSerializer(many=True)
    
    class Meta:
        model = Factura
        fields = ('venta', 'serie', 'cliente_rfc', 'cliente_nombre', 'cliente_email',
                 'cliente_codigo_postal', 'uso_cfdi', 'conceptos')
    
    def create(self, validated_data):
        conceptos_data = validated_data.pop('conceptos')
        
        # Generar folio
        serie = validated_data.get('serie', 'A')
        ultimo_folio = Factura.objects.filter(serie=serie).order_by('-folio').first()
        folio = 1 if not ultimo_folio else ultimo_folio.folio + 1
        validated_data['folio'] = folio
        
        # Generar folio fiscal temporal (será reemplazado al timbrar)
        validated_data['folio_fiscal'] = f"TEMP-{serie}-{folio}"
        validated_data['usuario'] = self.context['request'].user
        
        # Crear factura
        factura = Factura.objects.create(**validated_data)
        
        # Crear conceptos
        subtotal = Decimal('0')
        iva_total = Decimal('0')
        
        for concepto_data in conceptos_data:
            concepto = ConceptoFactura.objects.create(factura=factura, **concepto_data)
            subtotal += concepto.importe
            iva_total += concepto.iva
        
        # Actualizar totales
        factura.subtotal = subtotal
        factura.iva = iva_total
        factura.total = subtotal + iva_total
        factura.save()
        
        return factura

class FacturaTimbrarSerializer(serializers.Serializer):
    """Serializer para timbrar una factura con Facturapi"""
    pass