from django.urls import path, include
from rest_framework.routers import DefaultRouter

from content.views import (
    BlogViewSet, PostViewSet, CommentViewSet, BlogPostsListView, SubscribesListView,
    MyPostsListView, PostCommentsListView
)

router = DefaultRouter()
router.register("blog", BlogViewSet)
router.register("post", PostViewSet)
router.register("comment", CommentViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('blog/<slug>/posts', BlogPostsListView.as_view(), name='blog-posts-list'),
    path('blog/subscribes', SubscribesListView.as_view(), name='user-subscribes-list'),
    path('post/my', MyPostsListView.as_view(), name='user-posts-list'),
    path('post/<slug>/comments', PostCommentsListView.as_view(), name='post-comments-list'),
]
