from django.conf import settings
from django.db import models
from django.db.models import F
from django.urls import reverse

from taggit.managers import TaggableManager


class Blog(models.Model):
    """
    Сущность блога

    Поля сущности:
     * `slug` - слаг, уникальное поле (имя создателя-заголовок)
     * `title` - заголовок блога
     * `description` - описание блога
     * `created_at` - время и дата создания блога
     * `updated_at` - время и дата последнего обновления блога (по дате последней публикации)
     * `authors` - авторы, добавляющие посты в блог (User MTM rel)
     * `owner` - владелец блога (User OTM rel)
    """
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=255)
    description = models.CharField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True)
    authors = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='authors')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL,
                              on_delete=models.CASCADE,
                              related_name='owner')

    class Meta:
        get_latest_by = "-updated_at"
        ordering = [F('updated_at').desc(nulls_last=True)]
        indexes = [models.Index(fields=[
            "slug",
            "-updated_at",
            "title",
            "owner",
        ])]

    def get_absolute_url(self):
        return reverse("blog_detail", kwargs={"slug": self.slug})

    def __str__(self):
        return self.title

    @property
    def total_subscribers(self):
        return Subscription.objects.filter(blog=self).count()

    @staticmethod
    def get_user_field_name():
        return "owner"


class Post(models.Model):
    """
    Сущность поста

    Поля сущности:
     * `slug` - слаг, уникальное поле (HEX(Blog_ID)-заголовок)
     * `title` - заголовок поста
     * `body` - содержание поста
     * `is_published` - флаг публикации поста
     * `created_at` - время и дата публикации поста
     * `views` - Счётчик просмотров поста
     * `blog` - блог, в котором существует пост (Blog OTM rel)
     * `author` - автор поста (User OTM rel)
     * `tags` - менеджер тегов (Taggit)
    """
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=255)
    body = models.CharField()
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(null=True)
    views = models.IntegerField(default=0)
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    tags = TaggableManager()

    class Meta:
        get_latest_by = "-created_at"
        ordering = [F('created_at').desc(nulls_last=True)]
        indexes = [models.Index(fields=[
            "slug",
            "-created_at",
            "title",
            "views",
            "author"
        ])]

    def get_absolute_url(self):
        return reverse("post_detail", kwargs={"slug": self.slug})

    def __str__(self):
        return self.title

    @property
    def total_likes(self):
        return Like.objects.filter(post=self).count()

    @staticmethod
    def get_user_field_name():
        return "author"


class Comment(models.Model):
    """
    Сущность комментария

    Поля сущности:
     * `body` - содержание комментария
     * `created_at` - время и дата создания комментария
     * `post` - пост, в котором существует комментарий (Post OTM rel)
     * `commented_by` - автор комментария (User OTM rel)
    """
    body = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    commented_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        get_latest_by = "-created_at"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=[
            "-created_at",
            "post",
            "commented_by"
        ])]

    @staticmethod
    def get_user_field_name():
        return "commented_by"


class Like(models.Model):
    """
    Сущность лайка

    Связывающая сущность пользователя и поста: `Post` O<->M `Like` M<->O `User`

    Поля сущности:
     * `post` - ключ понравившегося поста (Post OTM rel)
     * `created_at` - время и дата создания сущности
     * `liked_by` - автор лайка (User OTM rel)
    """
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    liked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING)

    class Meta:
        indexes = [models.Index(fields=[
            "post",
            "liked_by"
        ])]


class Subscription(models.Model):
    """
    Сущность подписки

    Связывающая сущность пользователя и блога: `Blog` O<->M `Subscribe` M<->O `User`

    Поля сущности:
     * `blog` - ключ блога для подписки (Blog OTM rel)
     * `created_at` - время и дата создания сущности
     * `user` - подписчик (User OTM rel)
    """
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        indexes = [models.Index(fields=[
            "user",
            "blog"
        ])]
