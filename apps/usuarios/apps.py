from django.apps import AppConfig

class UsuariosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.usuarios'
    verbose_name = 'Gestión de Usuarios'
    
    def ready(self):
        import apps.usuarios.signals  # Si tienes signals