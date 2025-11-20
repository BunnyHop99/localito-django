from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Factura

@receiver(post_save, sender=Factura)
def factura_timbrada(sender, instance, created, **kwargs):
    """
    Señal que se ejecuta cuando una factura es timbrada
    """
    if instance.status == 'timbrada' and instance.xml_url:
        print(f"Factura {instance.numero_completo} timbrada exitosamente")
        # Aquí puedes enviar email al cliente con la factura