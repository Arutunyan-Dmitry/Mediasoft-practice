from pytils.translit import slugify

from content.models import Subscription, Blog, Like


def generate_slug(beg_pt, end_pt):
    """
    Генератор двусоставного слага сущности
    :param beg_pt: 1-я часть слага
    :param end_pt: 2-я часть слага
    :return: слаг (транслит)
    """
    return slugify(beg_pt + '-' + end_pt)


def slug_valid(model, slug):
    """
    Проверка валидности слагов
    :param model: Модель бд сущности
    :param slug: слаг сущности
    :return: True / False
    """
    return not model.objects.filter(slug=slug).exists()


def slug_valid_upd(model, slug, instance):
    """
    Проверка валидности слагов (при обновлении сущности)
    :param model: Модель бд сущности
    :param slug: слаг сущности
    :param instance: экземпляр модели (сущность)
    :return: True / False
    """
    if not model.objects.filter(slug=slug).exists():
        return True
    qs = model.objects.filter(slug=slug)
    if qs.count() == 1 and qs.first() == instance:
        return True
    return False


def only_exist_users(author_model, authors):
    """
    Выборка существующих пользователей из списка
    :param author_model: Модель бд пользователя
    :param authors: Список имён пользователей
    :return: Список существующих имён пользователей
    """
    result_authors = []
    for author in authors:
        if author_model.objects.filter(username=author).exists():
            result_authors.append(author)
    return result_authors


def all_except_owner(instance, authors):
    """
    Удаление владельца блога из списка имён авторов
    :param instance: сущность блога
    :param authors: список авторов
    :return: список имён авторов
    """
    if instance.owner.username in authors:
        authors.remove(instance.owner.username)
    return authors


def all_except_blog_authors(instance, authors):
    """
    Удаление всех авторов блога из списка имён авторов
    :param instance: сущность блога
    :param authors: список авторов
    :return: список имён авторов
    """
    username_list = list(instance.authors.all().values_list('username', flat=True))
    return [item for item in authors if item not in username_list]


def only_blog_authors(instance, authors):
    """
    Выборка только авторов блога из списка имён пользователей
    :param instance: сущность блога
    :param authors: список авторов
    :return: список имён авторов
    """
    username_list = list(instance.authors.all().values_list('username', flat=True))
    return [item for item in authors if item in username_list]


def is_user_in_authors_field(blog_slug, user):
    """
    Является ли пользователь автором блога
    :param blog_slug: слаг блога
    :param user: сущность пользователя
    :return: True / False
    """
    if Blog.objects.filter(slug=blog_slug).exists():
        blog = Blog.objects.get(slug=blog_slug)
        return user in blog.authors.all()
    return False


def is_creator_or_admin(user, obj):
    if user.is_staff:
        return True
    try:
        obj_user = getattr(obj, obj.get_user_field_name(), None)
        return obj_user.pk == user.pk
    except:
        return False


def is_blog_owner(user, blog):
    try:
        blog_owner = getattr(blog, blog.get_user_field_name(), None)
        return blog_owner.pk == user.pk
    except:
        return False


def has_subscribed(instance, user):
    return Subscription.objects.filter(user=user, blog=instance).exists()


def was_liked(instance, user):
    return Like.objects.filter(post=instance, liked_by=user).exists()







