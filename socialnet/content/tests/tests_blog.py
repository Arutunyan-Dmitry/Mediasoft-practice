from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from content.models import Blog, Subscription

User = get_user_model()


class BlogLogicTests(APITestCase):
    """
    Тест кейс на логику прямых запросов блога
    """
    def setUp(self) -> None:
        User.objects.create_user(username='blog_owner', password='blog_owner')

    def test_list_blog(self):
        user = User.objects.get(username='blog_owner')
        url = reverse('blog-list')
        Blog.objects.create(slug="blogowner-test-blog", title="test-blog", owner=user)
        Blog.objects.create(slug="blogowner-test1-blog", title="test1-blog", owner=user)
        self.client.force_authenticate(user=user)
        response = self.client.get(path=url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("count"), 2)

    def test_create_blog(self):
        user = User.objects.get(username='blog_owner')
        url = reverse('blog-list')
        data = {'title': 'test-blog'}
        self.client.force_authenticate(user=user)
        response = self.client.post(path=url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Blog.objects.count(), 1)
        self.assertEqual(Blog.objects.get().slug, 'blogowner-test-blog')


class BlogDetailLogicTests(APITestCase):
    """
    Тест кейс на логику detail запросов блога
    """
    def setUp(self) -> None:
        user = User.objects.create_user(username='blog_owner', password='blog_owner')
        Blog.objects.create(slug="blogowner-test-blog", title="test-blog", owner=user)

    @staticmethod
    def get_blog_user():
        return Blog.objects.get(), User.objects.get(username="blog_owner")

    def test_retrieve_blog(self):
        blog, user = self.get_blog_user()
        url = reverse('blog-detail', kwargs={"slug": blog.slug})
        self.client.force_authenticate(user=user)
        response = self.client.get(path=url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('slug'), 'blogowner-test-blog')

    def test_update_blog(self):
        blog, user = self.get_blog_user()
        url = reverse('blog-detail', kwargs={"slug": blog.slug})
        data = {'title': 'test-updated-blog', 'description': 'Blog for test'}
        self.client.force_authenticate(user=user)
        response = self.client.put(path=url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Blog.objects.get().slug, 'blogowner-test-updated-blog')
        self.assertEqual(Blog.objects.get().description, 'Blog for test')

    def test_partial_update_blog(self):
        blog, user = self.get_blog_user()
        url = reverse('blog-detail', kwargs={"slug": blog.slug})
        data = {'description': 'Blog for partial update test'}
        self.client.force_authenticate(user=user)
        response = self.client.patch(path=url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Blog.objects.get().description, 'Blog for partial update test')

    def test_delete_blog(self):
        blog, user = self.get_blog_user()
        url = reverse('blog-detail', kwargs={"slug": blog.slug})
        self.client.force_authenticate(user=user)
        response = self.client.delete(path=url, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Blog.objects.count(), 0)

    def test_author_add_to_remove_from_blog(self):
        blog, user = self.get_blog_user()
        url = reverse('blog-author', kwargs={"slug": blog.slug})
        author = User.objects.create_user(username="author", password="author")
        data = {'authors': [author.username, ]}
        self.client.force_authenticate(user=user)
        response = self.client.post(path=url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(author in blog.authors.all())
        response = self.client.delete(path=url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(author in blog.authors.all())

    def test_subscribe_unsubscribe_get_subscriptions_blog(self):
        blog, user = self.get_blog_user()
        url = reverse('blog-subscribe', kwargs={"slug": blog.slug})
        subscriber = User.objects.create_user(username="subscriber", password="subscriber")
        self.client.force_authenticate(user=subscriber)
        response = self.client.post(path=url, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Subscription.objects.count(), 1)
        self.assertTrue(Subscription.objects.filter(blog=blog, user=subscriber).exists())

        list_url = reverse('user-subscribes-list')
        response = self.client.get(path=list_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("count"), 1)
        self.assertEqual(response.data.get("results")[0].get("slug"), blog.slug)

        response = self.client.delete(path=url, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Subscription.objects.count(), 0)


class BlogPermissionsTests(APITestCase):
    """
    Тест кейс прав доступа к запросам блога
    """
    def setUp(self) -> None:
        user = User.objects.create_user(username='blog_owner', password='blog_owner')
        Blog.objects.create(slug="blogowner-test-blog", title="test-blog", owner=user)
        User.objects.create_user(username='stranger', password='stranger')

    @staticmethod
    def get_blog_stranger_admin():
        return (
            Blog.objects.get(),
            User.objects.get(username="stranger"),
            User.objects.get(username="ADMIN")
        )

    @staticmethod
    def subtest_permission(client, auth_models, method, url, data=None):
        exact_statuses = []
        for i in range(len(auth_models)):
            if auth_models[i] is not None:
                client.force_authenticate(user=auth_models[i])
            if method == "GET":
                exact_statuses.append(client.get(url, data, format='json').status_code)
            elif method == "POST":
                exact_statuses.append(client.post(url, data, format='json').status_code)
            elif method == "PUT":
                exact_statuses.append(client.put(url, data, format='json').status_code)
            elif method == "PATCH":
                exact_statuses.append(client.patch(url, data, format='json').status_code)
            elif method == "DELETE":
                exact_statuses.append(client.delete(url, data, format='json').status_code)
        return exact_statuses

    def test_update_blog(self):
        blog, stranger, admin = self.get_blog_stranger_admin()
        url = reverse('blog-detail', kwargs={"slug": blog.slug})
        data = {'title': 'test-updated-blog', 'description': 'Blog for test'}
        auth_models = [None, stranger, admin]
        expect_status = [status.HTTP_401_UNAUTHORIZED,
                         status.HTTP_403_FORBIDDEN,
                         status.HTTP_200_OK]
        exact_status = self.subtest_permission(self.client, auth_models, "PUT", url, data)
        self.assertEqual(expect_status, exact_status)

    def test_partial_update_blog(self):
        blog, stranger, admin = self.get_blog_stranger_admin()
        url = reverse('blog-detail', kwargs={"slug": blog.slug})
        data = {'description': 'Blog for partial update test'}
        auth_models = [None, stranger, admin]
        expect_status = [status.HTTP_401_UNAUTHORIZED,
                         status.HTTP_403_FORBIDDEN,
                         status.HTTP_200_OK]
        exact_status = self.subtest_permission(self.client, auth_models, "PATCH", url, data)
        self.assertEqual(expect_status, exact_status)

    def test_delete_blog(self):
        blog, stranger, admin = self.get_blog_stranger_admin()
        url = reverse('blog-detail', kwargs={"slug": blog.slug})
        auth_models = [None, stranger, admin]
        expect_status = [status.HTTP_401_UNAUTHORIZED,
                         status.HTTP_403_FORBIDDEN,
                         status.HTTP_204_NO_CONTENT]
        exact_status = self.subtest_permission(self.client, auth_models, "DELETE", url)
        self.assertEqual(expect_status, exact_status)

    def test_author_add_to_remove_from_blog(self):
        blog, stranger, admin = self.get_blog_stranger_admin()
        url = reverse('blog-author', kwargs={"slug": blog.slug})
        author = User.objects.create_user(username="author", password="author")
        data = {'authors': [author.username, ]}
        auth_models = [None, stranger, admin]
        expect_status = [status.HTTP_401_UNAUTHORIZED,
                         status.HTTP_403_FORBIDDEN,
                         status.HTTP_204_NO_CONTENT]
        exact_status = self.subtest_permission(self.client, auth_models, "POST", url, data)
        self.assertEqual(expect_status, exact_status)

