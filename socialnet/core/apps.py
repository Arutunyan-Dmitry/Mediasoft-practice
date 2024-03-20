from django.apps import AppConfig
from django.db.models.signals import post_migrate


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        from . import signals                                   # регистрация post migrate сигнала
        post_migrate.connect(signals.create_initial_superuser)  # для начального создания администратора
