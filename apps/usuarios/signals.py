from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

Usuario = get_user_model()

@receiver(post_save, sender=Usuario)
def usuario_creado(sender, instance, created, **kwargs):
    """
    Señal que se ejecuta cuando se crea un usuario
    """
    if created:
        print(f"Nuevo usuario registrado: {instance.username}")
        # Aquí puedes enviar email de bienvenida