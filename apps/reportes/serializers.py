from rest_framework import serializers
from .models import ReporteGenerado

class ReporteGeneradoSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(source='usuario.get_full_name', read_only=True)
    
    class Meta:
        model = ReporteGenerado
        fields = '__all__'
        read_only_fields = ('usuario', 'fecha_generacion')