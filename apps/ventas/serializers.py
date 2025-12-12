from rest_framework import serializers
from .models import Venta, DetalleVenta
from apps.inventario.models import Producto

class DetalleVentaSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_codigo = serializers.CharField(source='producto.codigo', read_only=True)
    
    class Meta:
        model = DetalleVenta
        fields = '__all__'
        read_only_fields = ('venta', 'subtotal', 'costo_unitario', 'utilidad')

class DetalleVentaCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleVenta
        fields = ('producto', 'cantidad', 'precio_unitario')
    
    def validate(self, data):
        producto = data['producto']
        cantidad = data['cantidad']
        
        if producto.stock < cantidad:
            raise serializers.ValidationError(
                f"Stock insuficiente. Disponible: {producto.stock}"
            )
        
        return data

class VentaSerializer(serializers.ModelSerializer):
    detalles = DetalleVentaSerializer(many=True, read_only=True)
    usuario_nombre = serializers.CharField(source='usuario.get_full_name', read_only=True)
    total_items = serializers.IntegerField(source='detalles.count', read_only=True)
    dias_para_vencimiento = serializers.SerializerMethodField()
    esta_por_vencer = serializers.SerializerMethodField()
    
    class Meta:
        model = Venta
        fields = '__all__'
        read_only_fields = ('folio', 'subtotal', 'iva', 'total', 'usuario', 'fecha', 
                          'fecha_vencimiento', 'estado_credito')
    
    def get_dias_para_vencimiento(self, obj):
        return obj.dias_para_vencimiento()
    
    def get_esta_por_vencer(self, obj):
        return obj.esta_por_vencer()

class VentaListSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(source='usuario.get_full_name', read_only=True)
    total_items = serializers.SerializerMethodField()
    dias_para_vencimiento = serializers.SerializerMethodField()
    esta_por_vencer = serializers.SerializerMethodField()
    
    class Meta:
        model = Venta
        fields = ('id', 'folio', 'fecha', 'cliente_nombre', 'total', 'metodo_pago', 
                 'usuario_nombre', 'total_items', 'cancelada', 'dias_credito', 
                 'fecha_vencimiento', 'estado_credito', 'dias_para_vencimiento', 
                 'esta_por_vencer')
    
    def get_total_items(self, obj):
        return obj.detalles.count()
    
    def get_dias_para_vencimiento(self, obj):
        return obj.dias_para_vencimiento()
    
    def get_esta_por_vencer(self, obj):
        return obj.esta_por_vencer()

class VentaCreateSerializer(serializers.ModelSerializer):
    detalles = DetalleVentaCreateSerializer(many=True)
    
    class Meta:
        model = Venta
        fields = ('cliente_nombre', 'cliente_rfc', 'metodo_pago', 'observaciones', 
                 'detalles', 'dias_credito')
    
    def validate(self, data):
        # Validar que si es crédito, se especifiquen los días
        if data.get('metodo_pago') == 'credito' and not data.get('dias_credito'):
            raise serializers.ValidationError(
                "Para ventas a crédito debe especificar los días de crédito"
            )
        
        # Validar que solo se especifiquen días de crédito si el método es crédito
        if data.get('metodo_pago') != 'credito' and data.get('dias_credito'):
            raise serializers.ValidationError(
                "Solo puede especificar días de crédito para ventas a crédito"
            )
        
        return data
    
    def create(self, validated_data):
        detalles_data = validated_data.pop('detalles')
        
        # Generar folio
        ultimo_folio = Venta.objects.all().order_by('-id').first()
        if ultimo_folio:
            numero = int(ultimo_folio.folio.split('-')[1]) + 1
        else:
            numero = 1
        validated_data['folio'] = f"V-{numero:05d}"
        
        # Crear venta
        validated_data['usuario'] = self.context['request'].user
        venta = Venta.objects.create(**validated_data)
        
        # Crear detalles y actualizar stock
        for detalle_data in detalles_data:
            producto = detalle_data['producto']
            cantidad = detalle_data['cantidad']
            
            # Validar stock nuevamente
            if producto.stock < cantidad:
                venta.delete()
                raise serializers.ValidationError(
                    f"Stock insuficiente para {producto.nombre}"
                )
            
            # Crear detalle
            DetalleVenta.objects.create(
                venta=venta,
                costo_unitario=producto.precio_costo,
                **detalle_data
            )
            
            # Actualizar stock
            producto.stock -= cantidad
            producto.save()
        
        # Calcular totales
        venta.calcular_totales()
        
        return venta

class MarcarPagadoSerializer(serializers.Serializer):
    """Serializer para marcar una venta a crédito como pagada"""
    pass