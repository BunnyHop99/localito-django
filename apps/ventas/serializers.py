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
    
    class Meta:
        model = Venta
        fields = '__all__'
        read_only_fields = ('folio', 'subtotal', 'iva', 'total', 'usuario', 'fecha')

class VentaListSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(source='usuario.get_full_name', read_only=True)
    total_items = serializers.SerializerMethodField()
    
    class Meta:
        model = Venta
        fields = ('id', 'folio', 'fecha', 'cliente_nombre', 'total', 'metodo_pago', 
                 'usuario_nombre', 'total_items', 'cancelada')
    
    def get_total_items(self, obj):
        return obj.detalles.count()

class VentaCreateSerializer(serializers.ModelSerializer):
    detalles = DetalleVentaCreateSerializer(many=True)
    
    class Meta:
        model = Venta
        fields = ('cliente_nombre', 'cliente_rfc', 'metodo_pago', 'observaciones', 'detalles')
    
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