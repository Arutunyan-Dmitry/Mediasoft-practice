from django.http import Http404
from django_filters import rest_framework as rest_filters
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework import filters
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from content.filters import BlogFilter, PostFilter
from content.models import Blog, Post, Comment
from content.permissions import IsBlogAuthorOrAdmin, IsCreatorOrAdmin, IsCreatorBlogOwnerOrAdmin
from content.serializers import (
    BlogSerializer, AuthorSerializer, SubscribeSerializer, PostSerializer,
    CreatePostSerializer, LikeSerializer, PublishPostSerializer, CommentSerializer,
    CreateCommentSerializer, CreateOrUpdateBlogSerializer, UpdatePostSerializer
)


class BlogViewSet(viewsets.ModelViewSet):
    """
    Представление модели блога

     * базовый класс сериализатора - Сериализатор блога
     * базовый класс разрешения - Доступно всем
     * поле поиска - слаг блога
     * класс фильтрации и сортировки - Фильтр блога
     * поля для поиска - заголовок (содержание в), имя владельца (точное совпадение)
    """
    serializer_class = BlogSerializer
    permission_classes = [AllowAny, ]
    queryset = Blog.objects.all()
    lookup_field = "slug"
    filter_backends = (rest_filters.DjangoFilterBackend, filters.SearchFilter,)
    filterset_class = BlogFilter
    search_fields = ['title', '=owner__username']

    def get_permissions(self):
        if self.action in ["create", "subscribe", "unsubscribe", ]:
            self.permission_classes = [IsAuthenticated, ]
        elif self.action in ["update", "partial_update", "destroy", "author", ]:
            self.permission_classes = [IsCreatorOrAdmin, ]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update", ]:
            return CreateOrUpdateBlogSerializer
        elif self.action in ["author", ]:
            return AuthorSerializer
        elif self.action in ["subscribe", "unsubscribe", ]:
            return SubscribeSerializer
        return self.serializer_class

    @action(detail=True, methods=["POST", "DELETE"])
    def author(self, request, slug=None):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        if request.method == "POST":
            serializer.add_authors(serializer.validated_data)
        elif request.method == "DELETE":
            serializer.remove_authors(serializer.validated_data)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["POST", "DELETE"])
    def subscribe(self, request, slug=None):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        if request.method == "POST":
            serializer.subscribe(serializer.validated_data)
        elif request.method == "DELETE":
            serializer.unsubscribe(serializer.validated_data)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SubscribesListView(ListAPIView):
    """
    Представление списка блогов, на которые подписан пользователь

     * базовый класс сериализатора - Сериализатор блога
     * базовый класс разрешения - Доступно авторизованным пользователям
     * класс фильтрации и сортировки - Фильтр блога
     * поля для поиска - заголовок (содержание в), имя владельца (точное совпадение)
    """
    queryset = Blog.objects.all()
    serializer_class = BlogSerializer
    permission_classes = [IsAuthenticated, ]
    filter_backends = (rest_filters.DjangoFilterBackend, filters.SearchFilter,)
    filterset_class = BlogFilter
    search_fields = ['title', '=owner__username']

    def get_queryset(self):
        return Blog.objects.filter(subscription__user=self.request.user)


class BlogPostsListView(ListAPIView):
    """
    Представление списка постов определённого блога

     * базовый класс сериализатора - Сериализатор поста
     * базовый класс разрешения - Доступно всем
     * класс фильтрации и сортировки - Фильтр поста
     * поля для поиска - заголовок (содержание в), имя автора (точное совпадение)
    """
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [AllowAny, ]
    filter_backends = (rest_filters.DjangoFilterBackend, filters.SearchFilter,)
    filterset_class = PostFilter
    search_fields = ['title', '=author__username']

    def get_queryset(self):
        blog_slug = self.kwargs.get('slug')                   # Исключение несуществующего блога
        if not Blog.objects.filter(slug=blog_slug).exists():
            raise Http404
        blog = Blog.objects.get(slug=blog_slug)                                 # Неопубликованные посты
        if not self.request.user.is_staff and self.request.user != blog.owner:  # доступны только администратору
            return Post.objects.filter(blog=blog, is_published=True)            # или владельцу блога
        return Post.objects.filter(blog=blog)


class PostViewSet(viewsets.ModelViewSet):
    """
    Представление модели поста

     * базовый класс сериализатора - Сериализатор поста
     * базовый класс разрешения - Доступно всем
     * поле поиска - слаг поста
     * класс фильтрации и сортировки - Фильтр поста
     * поля для поиска - заголовок (содержание в), имя автора (точное совпадение)
    """
    serializer_class = PostSerializer
    permission_classes = [AllowAny, ]
    queryset = Post.objects.all()
    lookup_field = "slug"
    filter_backends = (rest_filters.DjangoFilterBackend, filters.SearchFilter,)
    filterset_class = PostFilter
    search_fields = ['title', '=author__username']

    def get_permissions(self):
        if self.action in ["create", ]:
            self.permission_classes = [IsBlogAuthorOrAdmin, ]
        elif self.action in ["update", "partial_update", "publish", ]:
            self.permission_classes = [IsCreatorOrAdmin, ]
        elif self.action in ["destroy", ]:
            self.permission_classes = [IsCreatorBlogOwnerOrAdmin]
        elif self.action in ["like", ]:
            self.permission_classes = [IsAuthenticated, ]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action in ["create", ]:
            return CreatePostSerializer
        elif self.action in ["update", "partial_update", ]:
            return UpdatePostSerializer
        elif self.action in ["publish", ]:
            self.serializer_class = PublishPostSerializer
        elif self.action in ["like", ]:
            self.serializer_class = LikeSerializer
        return self.serializer_class

    def list(self, request, *args, **kwargs):
        if not request.user.is_staff:
            self.queryset = Post.objects.filter(is_published=True)
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        if not instance.is_published and not request.user.is_staff and request.user != instance.author:
            raise Http404
        if instance.is_published:
            instance.views += 1
            instance.save()
        return Response(serializer.data)

    @action(detail=True, methods=["POST"])
    def publish(self, request, slug=None):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.publish()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["POST", "DELETE"])
    def like(self, request, slug=None):
        instance = self.get_object()
        if not instance.is_published:
            raise Http404
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        if request.method == "POST":
            serializer.like(serializer.validated_data)
        elif request.method == "DELETE":
            serializer.remove_like(serializer.validated_data)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyPostsListView(ListAPIView):
    """
    Представление списка постов, созданных пользователем

     * базовый класс сериализатора - Сериализатор поста
     * базовый класс разрешения - Доступно авторизованным пользователям
     * класс фильтрации и сортировки - Фильтр поста
     * поля для поиска - заголовок (содержание в)
    """
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated, ]
    filter_backends = (rest_filters.DjangoFilterBackend, filters.SearchFilter,)
    filterset_class = PostFilter
    search_fields = ['title']

    def get_queryset(self):
        return Post.objects.filter(author=self.request.user)


class CommentViewSet(mixins.CreateModelMixin,
                     mixins.RetrieveModelMixin,
                     mixins.UpdateModelMixin,
                     mixins.DestroyModelMixin,
                     GenericViewSet):
    """
    Представление модели комментария

     * базовый класс сериализатора - Сериализатор комментария
     * базовый класс разрешения - Доступно всем
    """
    serializer_class = CommentSerializer
    permission_classes = [AllowAny, ]
    queryset = Comment.objects.all()

    def get_permissions(self):
        if self.action in ["create", ]:
            self.permission_classes = [IsAuthenticated, ]
        elif self.action in ["update", "partial_update", "destroy", ]:
            self.permission_classes = [IsCreatorOrAdmin, ]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action in ["create", ]:
            return CreateCommentSerializer
        return self.serializer_class


class PostCommentsListView(ListAPIView):
    """
    Представление списка комментариев поста

     * базовый класс сериализатора - Сериализатор комментария
     * базовый класс разрешения - Доступно всем
    """
    serializer_class = CommentSerializer
    permission_classes = [AllowAny, ]
    queryset = Comment.objects.all()

    def get_queryset(self):
        post_slug = self.kwargs.get('slug')                   # Исключение несуществующего поста
        if not Post.objects.filter(slug=post_slug).exists():
            raise Http404
        post = Post.objects.get(slug=post_slug)
        return Comment.objects.filter(post=post)
