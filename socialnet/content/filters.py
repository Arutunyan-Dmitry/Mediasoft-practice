from django.db.models import F, Count
from django_filters import DateFilter, OrderingFilter, ModelMultipleChoiceFilter
from django_filters.constants import EMPTY_VALUES
from django_filters.rest_framework import FilterSet
from taggit.models import Tag

from content.models import Blog, Post


class NullLastOrderingFilter(OrderingFilter):
    """
    Сортировщик объектов, всегда помещающий null-значения в конец
    """
    @staticmethod
    def _f_order_by(qs, field):
        if field.startswith("-"):
            field_name = field[1:]
            return qs.order_by(F(field_name).desc(nulls_last=True))
        else:
            return qs.order_by(F(field).asc(nulls_last=True))

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs
        ordering = [
            self.get_ordering_value(param)
            for param in value
            if param not in EMPTY_VALUES
        ]
        return self._f_order_by(qs, *ordering)


class BlogRelevanceOrderingFilter(NullLastOrderingFilter):
    """
    Сортировщик блогов по актуальности
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.extra['choices'] += [
            ('relevance', 'Relevance'),
            ('-relevance', 'Relevance (descending)'),
        ]

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs
        for field in value:
            if field in ['relevance', '-relevance']:
                if field.startswith("-"):
                    return qs.annotate(subscribers=Count('subscription'))\
                        .order_by('subscribers', F('updated_at').asc(nulls_last=True))
                else:
                    return qs.annotate(subscribers=Count('subscription'))\
                        .order_by('-subscribers', F('updated_at').desc(nulls_last=True))
        return super().filter(qs, value)


class PostRelevanceOrderingFilter(NullLastOrderingFilter):
    """
    Сортировщик постов по актуальности и кол-ву лайков
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.extra['choices'] += [
            ('likes', 'Likes'),
            ('-likes', 'Likes (descending)'),
            ('relevance', 'Relevance'),
            ('-relevance', 'Relevance (descending)'),
        ]

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs
        for field in value:
            if field in ['likes', '-likes']:
                if field.startswith("-"):
                    return qs.annotate(num_likes=Count('like')).order_by('num_likes')
                else:
                    return qs.annotate(num_likes=Count('like')).order_by('-num_likes')
            elif field in ['relevance', '-relevance']:
                if field.startswith("-"):
                    return qs.annotate(num_likes=Count('like'))\
                        .order_by('num_likes', 'views', F('created_at').asc(nulls_last=True))
                else:
                    return qs.annotate(num_likes=Count('like'))\
                        .order_by('-num_likes', '-views', F('created_at').desc(nulls_last=True))
        return super().filter(qs, value)


class BlogFilter(FilterSet):
    """
    Фильтр, сортировщик блогов

    Атрибуты фильтрации:
     * `date_from` - по дате "от"
     * `date_to` - по дате "до"
    Параметры сортировки:
     * 'title' - по заголовку ↑↓
     * `date` - по дате последней публикации ↑↓
     * `relevance` - по актуальности ↑↓
    """
    date_from = DateFilter(field_name='updated_at', lookup_expr="gt")
    date_to = DateFilter(field_name='updated_at', lookup_expr="lt")
    ordering = BlogRelevanceOrderingFilter(
        fields=(
            ('title', 'title'),
            ('updated_at', 'date'),
        ),
        field_name='ordering',
    )

    class Meta:
        model = Blog
        fields = ['title', 'updated_at', ]


class PostFilter(FilterSet):
    """
    Фильтр, сортировщик постов

    Атрибуты фильтрации:
     * `date_from` - по дате "от"
     * `date_to` - по дате "до"
     * `tags` - по тегу (Taggit)
    Параметры сортировки:
     * 'title' - по заголовку ↑↓
     * `date` - по дате публикации ↑↓
     * `like` - по кол-ву лайков ↑↓
     * `relevance` - по актуальности ↑↓
    """
    date_from = DateFilter(field_name='created_at', lookup_expr="gt")
    date_to = DateFilter(field_name='created_at', lookup_expr="lt")
    tags = ModelMultipleChoiceFilter(field_name='tags__name', to_field_name='name', queryset=Tag.objects.all())
    ordering = PostRelevanceOrderingFilter(
        fields=(
            ('title', 'title'),
            ('created_at', 'date')
        ),
        field_name='ordering',
    )

    class Meta:
        model = Post
        fields = ['title', 'created_at', 'tags', ]
