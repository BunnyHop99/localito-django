from rest_framework import serializers
from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer
from djoser.serializers import UserSerializer as BaseUserSerializer
from .models import Usuario

class UserCreateSerializer(BaseUserCreateSerializer):
    class Meta(BaseUserCreateSerializer.Meta):
        model = Usuario
        fields = ('id', 'username', 'email', 'password', 'first_name', 'last_name', 'rol', 'telefono')

class UserSerializer(BaseUserSerializer):
    class Meta(BaseUserSerializer.Meta):
        model = Usuario
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'rol', 'telefono', 'foto', 'activo', 'date_joined')
        read_only_fields = ('date_joined',)

class UsuarioListSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.SerializerMethodField()
    
    class Meta:
        model = Usuario
        fields = ('id', 'username', 'email', 'nombre_completo', 'rol', 'activo', 'fecha_creacion')
    
    def get_nombre_completo(self, obj):
        return obj.get_full_name() or obj.username