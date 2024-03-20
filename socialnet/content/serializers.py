from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError
from rest_framework.fields import empty
from taggit.serializers import TaggitSerializer, TagListSerializerField

from content.models import Blog, Subscription, Post, Like, Comment
from content.utils import (
    generate_slug, slug_valid, only_exist_users, all_except_owner, all_except_blog_authors,
    only_blog_authors, has_subscribed, was_liked, slug_valid_upd
)


class SlugSerializer(serializers.Serializer):
    """
    Сериализатор создания двусоставных слагов

    Параметры инициализации `__init__()`
     * `model` - класс модели в бд, для объекта которого создаётся слаг
     * `beg-slug` - 1-я составляющая слага
     * `end_slug` - 2-я составляющая слага
    """
    default_error_messages = {
        "data": _("Invalid data provided."),
        "unique": _("The same entity had already been created.")
    }

    def __init__(self, instance=None, data=empty, **kwargs):
        super().__init__(instance, data, **kwargs)
        self.model = None
        self.beg_slug = None
        self.end_slug = None

    def validate(self, attrs):
        validated_data = super().validate(attrs)
        if self.model is not None and self.beg_slug is not None and self.end_slug is not None:
            try:
                slug = generate_slug(self.beg_slug, self.end_slug)                 # генерация слага
            except AttributeError:
                key_error = "data"
                raise ValidationError(
                    {"data": [self.error_messages[key_error]]}, code=key_error
                )
            if self.context["request"].method in ["PUT", "PATCH"]:
                if not slug_valid_upd(self.model, slug, self.instance):            # проверка валидности слага (обновление)
                    key_error = "unique"
                    raise ValidationError(
                        {"title": [self.error_messages[key_error]]}, code=key_error
                    )
            else:
                if not slug_valid(self.model, slug):                               # проверка валидности слага (создание)
                    key_error = "unique"
                    raise ValidationError(
                        {"title": [self.error_messages[key_error]]}, code=key_error
                    )
            validated_data["slug"] = slug
        return validated_data


class BlogSerializer(serializers.ModelSerializer):
    """
    Основной сериализатор сущности блогов

    Предполагает использование методами: retrieve, list, delete
    """
    owner = serializers.SerializerMethodField()
    authors = serializers.SerializerMethodField()
    subscribes = serializers.SerializerMethodField()

    @staticmethod
    def get_owner(obj):
        return getattr(obj, obj.get_user_field_name()).username

    @staticmethod
    def get_authors(obj):
        return [author.username for author in obj.authors.all()]

    @staticmethod
    def get_subscribes(obj):
        return obj.total_subscribers

    class Meta:
        model = Blog
        fields = ("slug", "title", "description", "created_at", "updated_at", "subscribes", "authors", "owner")
        read_only_fields = ("slug", "authors", "updated_at", "created_at", "subscribes", "authors", "owner")
        lookup_field = "slug"


class CreateOrUpdateBlogSerializer(SlugSerializer, BlogSerializer):
    """
    Сериализатор создания и обновления сущности блогов
    """
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Blog
        fields = ("title", "description", "owner")
        read_only_fields = ("slug", "authors", "updated_at", "created_at", "authors", "subscribers")

    def validate(self, attrs):
        if 'title' in attrs:
            self.model = self.Meta.model                 # Генерация слага
            if self.instance is None:                    # 1-я часть - имя владельца
                self.beg_slug = attrs.get("owner").username
            else:
                self.beg_slug = self.instance.owner.username
            self.end_slug = attrs.get("title")           # 2-я часть - заголовок блога (транслит)
        validated_data = super().validate(attrs)
        return validated_data

    def create(self, validated_data):
        blog = super().create(validated_data)
        blog.authors.add(validated_data.get("owner"))  # Добавление владельца как автора
        blog.save()                                    # при создании блога
        return blog

    def update(self, instance, validated_data):
        validated_data.pop("owner", None)
        return super().update(instance, validated_data)


class AuthorSerializer(serializers.Serializer):
    """
    Сериализатор авторов в блоге
    """
    authors = serializers.ListField()
    default_error_messages = {
        "exists": _("Authors do not exists."),
        "blog_authors_add": _("Authors had been already added."),
        "blog_authors_delete": _("Authors do not exists in the blog."),
        "owner_action": _("Owner could not be added to or deleted from authors."),
    }

    def validate(self, attrs):
        validated_data = super().validate(attrs)
        validated_data["authors"] = only_exist_users(User, attrs.get("authors"))
        if not bool(validated_data["authors"]):   # Наличие записей после исключения
            key_error = "exists"                  # несуществующих пользователей
            raise ValidationError(
                {"authors": [self.error_messages[key_error]]}, code=key_error
            )
        validated_data["authors"] = all_except_owner(self.instance, validated_data["authors"])
        if not bool(validated_data["authors"]):   # Наличие записей после исключения
            key_error = "owner_action"            # владельца
            raise ValidationError(
                {"authors": [self.error_messages[key_error]]}, code=key_error
            )
        if self.context["request"].method == "POST":
            """ При добавлении авторов """
            validated_data["authors"] = all_except_blog_authors(self.instance, validated_data["authors"])
            if not bool(validated_data["authors"]):  # Наличие записей после исключения
                key_error = "blog_authors_add"       # уже добавленных авторов
                raise ValidationError(
                    {"authors": [self.error_messages[key_error]]}, code=key_error
                )
        elif self.context["request"].method == "DELETE":
            """ При удалении авторов """
            validated_data["authors"] = only_blog_authors(self.instance, validated_data["authors"])
            if not bool(validated_data["authors"]):  # Наличие записей после исключения
                key_error = "blog_authors_delete"    # несуществующих авторов блога
                raise ValidationError(
                    {"authors": [self.error_messages[key_error]]}, code=key_error
                )
        return validated_data

    def add_authors(self, validated_data):
        blog = self.instance
        addition_users = User.objects.filter(username__in=validated_data.get("authors"))
        blog.authors.add(*addition_users)
        blog.save()
        return blog

    def remove_authors(self, validated_data):
        blog = self.instance
        removing_users = User.objects.filter(username__in=validated_data.get("authors"))
        blog.authors.remove(*removing_users)
        blog.save()
        return blog


class SubscribeSerializer(serializers.Serializer):
    """
    Сериализатор подписок
    """
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    default_error_messages = {
        "subscribed": _("User has already subscribed."),
        "unsubscribed": _("User had not been subscribed."),
    }

    def validate(self, attrs):
        validated_data = super().validate(attrs)
        if self.context["request"].method == "POST":
            """ При подписке """
            if has_subscribed(self.instance, validated_data["user"]):
                key_error = "subscribed"     # Исключить уже оформленную подписку
                raise ValidationError(
                    {"user": [self.error_messages[key_error]]}, code=key_error
                )
        elif self.context["request"].method == "DELETE":
            """ При отписке """
            if not has_subscribed(self.instance, validated_data["user"]):
                key_error = "unsubscribed"   # Исключить несуществующую подписку
                raise ValidationError(
                    {"user": [self.error_messages[key_error]]}, code=key_error
                )
        return validated_data

    def subscribe(self, validated_data):
        return Subscription.objects.create(user=validated_data.get("user"), blog=self.instance)

    def unsubscribe(self, validated_data):
        return Subscription.objects.get(user=validated_data.get("user"), blog=self.instance).delete()


class PostSerializer(TaggitSerializer, serializers.ModelSerializer):
    """
    Основной сериализатор сущности постов

    Предполагает использование методами: retrieve, list, delete
    """
    tags = TagListSerializerField()
    author = serializers.SerializerMethodField()
    likes = serializers.SerializerMethodField()

    @staticmethod
    def get_likes(obj):
        return obj.total_likes

    @staticmethod
    def get_author(obj):
        return getattr(obj, obj.get_user_field_name()).username

    class Meta:
        model = Post
        fields = ("slug", "title", "body", "is_published", "created_at", "likes", "views", "tags", "author")
        read_only_fields = ("slug", "is_published", "created_at", "likes", "views", "author")
        lookup_field = "slug"


class CreatePostSerializer(SlugSerializer, PostSerializer):
    """
    Сериализатор создания сущности поста
    """
    blog_slug = serializers.CharField(source="blog")
    author = serializers.HiddenField(default=serializers.CurrentUserDefault())
    default_error_messages = {
        "slug": _("Wrong blog slug was provided."),
    }

    class Meta:
        model = Post
        fields = ("blog_slug", "title", "body", "tags", "author")

    def validate(self, attrs):
        self.model = self.Meta.model
        try:
            blog = Blog.objects.get(slug=attrs.get("blog"))   # Поиск сущности блога по слагу
            attrs["blog"] = blog
        except (Blog.DoesNotExist, AttributeError):
            key_error = "slug"
            raise ValidationError(
                {"blog_slug": [self.error_messages[key_error]]}, code=key_error
            )
        self.beg_slug = attrs.get("title")      # 1-я часть - заголовок поста
        self.end_slug = hex(blog.id)[2:]        # 2-я часть - UUID блога в hex формате
        validated_data = super().validate(attrs)
        return validated_data


class UpdatePostSerializer(SlugSerializer, PostSerializer):
    """
    Сериализатор обновления сущности поста
    """
    class Meta:
        model = Post
        fields = ("title", "body", "tags", "author")

    def validate(self, attrs):
        if 'title' in attrs:
            self.model = self.Meta.model                    # Обновление слага
            self.beg_slug = attrs.get("title")              # 1-я часть - заголовок поста
            self.end_slug = hex(self.instance.blog.id)[2:]  # 2-я часть - UUID блога в hex формате
        validated_data = super().validate(attrs)
        return validated_data


class PublishPostSerializer(serializers.Serializer):
    """
    Сериализатор публикации поста
    """
    default_error_messages = {
        "published": _("Post had been already published."),
    }

    def validate(self, attrs):
        validated_data = super().validate(attrs)
        if self.instance.is_published:
            key_error = "published"             # Исключение уже опубликованного поста
            raise ValidationError(
                {"published": [self.error_messages[key_error]]}, code=key_error
            )
        return validated_data

    def publish(self):
        post = self.instance
        post.is_published = True
        post.created_at = timezone.now()      # Добавление времени создания поста
        post.save()
        blog = Blog.objects.get(pk=post.blog.pk)
        blog.updated_at = post.created_at     # Обновление даты последней публикации блога
        blog.save()


class LikeSerializer(serializers.Serializer):
    """
    Сериализатор лайков
    """
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    default_error_messages = {
        "liked": _("That post had been already liked by this user."),
        "no-like": _("That post had not been liked by this user."),
    }

    def validate(self, attrs):
        validated_data = super().validate(attrs)
        if self.context["request"].method == "POST":
            """ При лайке поста """
            if was_liked(self.instance, validated_data["user"]):
                key_error = "liked"      # Исключение существующего лайка
                raise ValidationError(
                    {"like": [self.error_messages[key_error]]}, code=key_error
                )
        if self.context["request"].method == "DELETE":
            """ При удалении лайка """
            if not was_liked(self.instance, validated_data["user"]):
                key_error = "no-like"     # Исключение несуществующего лайка
                raise ValidationError(
                    {"like": [self.error_messages[key_error]]}, code=key_error
                )
        return validated_data

    def like(self, validated_data):
        return Like.objects.create(post=self.instance, liked_by=validated_data.get("user"))

    def remove_like(self, validated_data):
        return Like.objects.get(post=self.instance, liked_by=validated_data.get("user")).delete()


class CommentSerializer(serializers.ModelSerializer):
    """
    Основной сериализатор сущности комментария

    Предполагает использование методами: retrieve, list, update, partial_update, delete
    """
    commented_by = serializers.SerializerMethodField()

    @staticmethod
    def get_commented_by(obj):
        return getattr(obj, obj.get_user_field_name()).username

    class Meta:
        model = Comment
        fields = ("body", "created_at", "post", "commented_by")
        read_only_fields = ("created_at", "post", "commented_by")


class CreateCommentSerializer(CommentSerializer):
    """
    Сериализатор создания сущности комментария
    """
    commented_by = serializers.HiddenField(default=serializers.CurrentUserDefault())
    post_slug = serializers.CharField(source="post")
    default_error_messages = {
        "slug": _("Wrong post slug was provided."),
        "publish": _("Post had not been published yet."),
    }

    class Meta:
        model = Comment
        fields = ("body", "post_slug", "commented_by")

    def validate(self, attrs):
        try:
            post = Post.objects.get(slug=attrs.get("post"))
            attrs["post"] = post
        except (Post.DoesNotExist, AttributeError):
            key_error = "slug"                          # Исключение несуществующего поста
            raise ValidationError(
                {"post_slug": [self.error_messages[key_error]]}, code=key_error
            )
        if not post.is_published:
            key_error = "publish"                       # Исключение неопубликованного поста
            raise ValidationError(
                {"post_slug": [self.error_messages[key_error]]}, code=key_error
            )
        validated_data = super().validate(attrs)
        return validated_data
