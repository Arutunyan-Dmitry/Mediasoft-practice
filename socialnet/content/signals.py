from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User

from content.models import Blog
from content.utils import generate_slug


@receiver(pre_save, sender=User)
def handle_username_change(sender, instance, **kwargs):
    """
    Обработчик сигнала при изменении имени пользователя
    для обновления слагов зависимых сущностей блогов
    """
    if instance.pk is not None:
        try:
            old_user = User.objects.get(pk=instance.pk)
            if instance.username != old_user.username:
                blogs = Blog.objects.filter(owner=old_user)
                for blog in blogs:
                    blog.slug = generate_slug(instance.username, blog.title)
                    blog.save()
        except User.DoesNotExist:
            pass
