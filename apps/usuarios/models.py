from django.contrib.auth.models import AbstractUser
from django.db import models

class Usuario(AbstractUser):
    ROLES = (
        ('admin', 'Administrador'),
        ('vendedor', 'Vendedor'),
        ('almacen', 'Almacén'),
    )
    
    rol = models.CharField(max_length=20, choices=ROLES, default='vendedor')
    telefono = models.CharField(max_length=15, blank=True, null=True)
    foto = models.ImageField(upload_to='usuarios/', blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    ultima_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'usuarios'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.rol})"