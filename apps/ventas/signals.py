from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Producto

@receiver(post_save, sender=Producto)
def producto_creado(sender, instance, created, **kwargs):
    """
    Señal que se ejecuta cuando se crea un producto
    Aquí puedes agregar lógica adicional
    """
    if created:
        print(f"Nuevo producto creado: {instance.nombre}")
        # Aquí podrías enviar notificaciones, logs, etc.