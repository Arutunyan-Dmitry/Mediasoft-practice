from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from content.models import Blog, Post, Comment

User = get_user_model()


class CommentLogicTests(APITestCase):
    """
    Тест кейс на логику прямых запросов комментария
    """
    def setUp(self) -> None:
        user = User.objects.create_user(username='blog_owner', password='blog_owner')
        blog = Blog.objects.create(slug="blogowner-test-blog", title="test-blog", owner=user)
        blog.authors.add(user)
        blog.save()
        Post.objects.create(slug="published-post" + "-" + hex(blog.id)[2:], title="published-post", is_published=True, blog=blog, author=user)

    @staticmethod
    def get_post_user():
        return Post.objects.get(), User.objects.get(username="blog_owner")

    def test_list_comment(self):
        post, user = self.get_post_user()
        url = reverse('post-comments-list', kwargs={"slug": post.slug})
        Comment.objects.create(body="test comment", post=post, commented_by=user)
        Comment.objects.create(body="test comment 1", post=post, commented_by=user)
        self.client.force_authenticate(user=user)
        response = self.client.get(path=url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("count"), 2)

    def test_create_comment(self):
        post, user = self.get_post_user()
        url = reverse('comment-list')
        data = {
            'body': 'test comment body',
            'post_slug': post.slug
        }
        self.client.force_authenticate(user=user)
        response = self.client.post(path=url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(Comment.objects.get().body, 'test comment body')


class CommentLogicDetailTests(APITestCase):
    """
    Тест кейс на логику detail запросов комментария
    """
    def setUp(self) -> None:
        user = User.objects.create_user(username='blog_owner', password='blog_owner')
        blog = Blog.objects.create(slug="blogowner-test-blog", title="test-blog", owner=user)
        blog.authors.add(user)
        blog.save()
        post = Post.objects.create(slug="published-post" + "-" + hex(blog.id)[2:], title="published-post", is_published=True, blog=blog, author=user)
        Comment.objects.create(body='test comment body', post=post, commented_by=user)

    @staticmethod
    def get_comment_user():
        return Comment.objects.get(), User.objects.get(username="blog_owner")

    def test_retrieve_comment(self):
        comment, user = self.get_comment_user()
        url = reverse('comment-detail', kwargs={"pk": comment.id})
        self.client.force_authenticate(user=user)
        response = self.client.get(path=url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('body'), 'test comment body')

    def test_update_comment(self):
        comment, user = self.get_comment_user()
        url = reverse('comment-detail', kwargs={"pk": comment.id})
        data = {'body': 'test comment update body'}
        self.client.force_authenticate(user=user)
        response = self.client.put(path=url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Comment.objects.get().body, 'test comment update body')

    def test_partial_update_post(self):
        comment, user = self.get_comment_user()
        url = reverse('comment-detail', kwargs={"pk": comment.id})
        data = {'body': 'test comment update body'}
        self.client.force_authenticate(user=user)
        response = self.client.patch(path=url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Comment.objects.get().body, 'test comment update body')

    def test_delete_post(self):
        comment, user = self.get_comment_user()
        url = reverse('comment-detail', kwargs={"pk": comment.id})
        self.client.force_authenticate(user=user)
        response = self.client.delete(path=url, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Comment.objects.count(), 0)


