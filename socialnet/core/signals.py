from django.contrib.auth.models import User
from django.db.models.signals import post_migrate
from django.dispatch import receiver


@receiver(post_migrate)
def create_initial_superuser(sender, **kwargs):
    """
    Обработчик post-migrate сигнала, для начального создания администратора

     WARNING: Изменение начальных значений сущности администратора может привести
     к блокировке его функционала и нестабильной работы системы
    """
    if not User.objects.filter(is_superuser=True).exists():
        User.objects.create_superuser(
            username='ADMIN',
            password='admin'
        )
