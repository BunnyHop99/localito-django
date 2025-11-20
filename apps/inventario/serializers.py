from rest_framework import serializers
from .models import Categoria, Producto, MovimientoInventario

class CategoriaSerializer(serializers.ModelSerializer):
    total_productos = serializers.IntegerField(source='productos.count', read_only=True)
    
    class Meta:
        model = Categoria
        fields = '__all__'

class ProductoSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    stock_bajo = serializers.BooleanField(read_only=True)
    margen_utilidad = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    
    class Meta:
        model = Producto
        fields = '__all__'

class ProductoListSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    stock_bajo = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Producto
        # ✅ CORREGIDO: Agregado precio_costo, descripcion y categoria
        fields = ('id', 'codigo', 'nombre', 'descripcion', 'categoria', 'categoria_nombre', 
                 'stock', 'stock_minimo', 'precio_costo', 'precio_venta', 
                 'stock_bajo', 'activo')

class MovimientoInventarioSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    usuario_nombre = serializers.CharField(source='usuario.get_full_name', read_only=True)
    
    class Meta:
        model = MovimientoInventario
        fields = '__all__'
        read_only_fields = ('stock_anterior', 'stock_nuevo', 'usuario', 'fecha')

class MovimientoInventarioCreateSerializer(serializers.ModelSerializer):
    # ✅ NUEVO: Soporte para precio_unitario en entradas
    precio_unitario = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=False,
        write_only=True,
        help_text="Precio de compra unitario (solo para entradas)"
    )
    
    class Meta:
        model = MovimientoInventario
        fields = ('producto', 'tipo', 'cantidad', 'motivo', 'observaciones', 'precio_unitario')
    
    def validate(self, data):
        """Validaciones personalizadas"""
        if data['tipo'] == 'entrada' and 'precio_unitario' in data:
            if data['precio_unitario'] <= 0:
                raise serializers.ValidationError({
                    'precio_unitario': 'El precio unitario debe ser mayor a 0'
                })
        return data
    
    def create(self, validated_data):
        producto = validated_data['producto']
        tipo = validated_data['tipo']
        cantidad = validated_data['cantidad']
        precio_unitario = validated_data.pop('precio_unitario', None)
        
        # Guardar stock anterior
        validated_data['stock_anterior'] = producto.stock
        
        # Calcular nuevo stock y precio promedio si es entrada
        if tipo == 'entrada':
            # Si viene precio_unitario, calcular CPP
            if precio_unitario is not None:
                stock_anterior = producto.stock
                costo_anterior = producto.precio_costo
                
                # Calcular Costo Promedio Ponderado
                total_stock = stock_anterior + cantidad
                if total_stock > 0:
                    nuevo_costo = ((stock_anterior * costo_anterior) + (cantidad * precio_unitario)) / total_stock
                    producto.precio_costo = round(nuevo_costo, 2)
            
            producto.stock += cantidad
            
        elif tipo == 'salida':
            if producto.stock < cantidad:
                raise serializers.ValidationError("Stock insuficiente")
            producto.stock -= cantidad
            
        elif tipo == 'ajuste':
            producto.stock = cantidad
        
        validated_data['stock_nuevo'] = producto.stock
        validated_data['usuario'] = self.context['request'].user
        
        producto.save()
        return super().create(validated_data)
