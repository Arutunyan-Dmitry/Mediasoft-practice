import random
import string

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from content.models import Blog, Post

User = get_user_model()


class PostLogicTests(APITestCase):
    """
    Тест кейс на логику прямых запросов поста
    """
    def setUp(self) -> None:
        user = User.objects.create_user(username='blog_owner', password='blog_owner')
        blog = Blog.objects.create(slug="blogowner-test-blog", title="test-blog", owner=user)
        blog.authors.add(user)
        blog.save()

    @staticmethod
    def get_blog_user():
        return Blog.objects.get(), User.objects.get(username="blog_owner")

    def test_list_post(self):
        blog, user = self.get_blog_user()
        url = reverse('post-list')
        Post.objects.create(slug="test-post", title="test-post", is_published=True, blog=blog, author=user)
        Post.objects.create(slug="test-post-1", title="test-post-1", is_published=True, blog=blog, author=user)
        self.client.force_authenticate(user=user)
        response = self.client.get(path=url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("count"), 2)

    def test_list_post_my(self):
        blog, user = self.get_blog_user()
        url = reverse('user-posts-list')
        Post.objects.create(slug="test-post", title="test-post", is_published=True, blog=blog, author=user)
        self.client.force_authenticate(user=user)
        response = self.client.get(path=url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("count"), 1)

    def test_list_blog_post(self):
        blog, user = self.get_blog_user()
        url = reverse('blog-posts-list', kwargs={"slug": blog.slug})
        Post.objects.create(slug="test-post", title="test-post", is_published=True, blog=blog, author=user)
        self.client.force_authenticate(user=user)
        response = self.client.get(path=url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("count"), 1)

    def test_create_post(self):
        blog, user = self.get_blog_user()
        url = reverse('post-list')
        data = {
            'title': 'test-post',
            'body': 'test post body',
            'tags': [],
            'blog_slug': blog.slug
        }
        self.client.force_authenticate(user=user)
        response = self.client.post(path=url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Post.objects.count(), 1)
        self.assertEqual(Post.objects.get().title, 'test-post')


class PostLogicDetailTests(APITestCase):
    """
    Тест кейс на логику detail запросов поста
    """
    def setUp(self) -> None:
        user = User.objects.create_user(username='blog_owner', password='blog_owner')
        blog = Blog.objects.create(slug="blogowner-test-blog", title="test-blog", owner=user)
        blog.authors.add(user)
        blog.save()
        Post.objects.create(slug="test-post", title="test-post", is_published=True, blog=blog, author=user)

    @staticmethod
    def get_post_user():
        return Post.objects.get(), User.objects.get(username="blog_owner")

    def test_retrieve_post(self):
        post, user = self.get_post_user()
        url = reverse('post-detail', kwargs={"slug": post.slug})
        self.client.force_authenticate(user=user)
        response = self.client.get(path=url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('slug'), 'test-post')

    def test_update_post(self):
        post, user = self.get_post_user()
        url = reverse('post-detail', kwargs={"slug": post.slug})
        data = {'title': 'test-updated-post', 'body': 'Post for test', 'tags': []}
        self.client.force_authenticate(user=user)
        response = self.client.put(path=url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Post.objects.get().title, 'test-updated-post')
        self.assertEqual(Post.objects.get().body, 'Post for test')

    def test_partial_update_post(self):
        post, user = self.get_post_user()
        url = reverse('post-detail', kwargs={"slug": post.slug})
        data = {'body': 'Post for partial update test'}
        self.client.force_authenticate(user=user)
        response = self.client.patch(path=url, data=data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Post.objects.get().body, 'Post for partial update test')

    def test_delete_post(self):
        post, user = self.get_post_user()
        url = reverse('post-detail', kwargs={"slug": post.slug})
        self.client.force_authenticate(user=user)
        response = self.client.delete(path=url, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Post.objects.count(), 0)

    def test_publish_post(self):
        post, user = self.get_post_user()
        post.is_published = False
        post.save()
        url = reverse('post-publish', kwargs={"slug": post.slug})
        self.client.force_authenticate(user=user)
        response = self.client.post(path=url, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(Post.objects.get().is_published)

    def test_post_add_remove_like(self):
        post, user = self.get_post_user()
        url = reverse('post-like', kwargs={"slug": post.slug})
        self.client.force_authenticate(user=user)
        response = self.client.post(path=url, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Post.objects.get().total_likes, 1)
        response = self.client.delete(path=url, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Post.objects.get().total_likes, 0)


class PostPermissionsTests(APITestCase):
    """
    Тест кейс прав доступа к запросам поста
    """
    def setUp(self) -> None:
        owner = User.objects.create_user(username='owner', password='owner')
        author = User.objects.create_user(username='author', password='author')
        User.objects.create_user(username='stranger', password='stranger')
        blog = Blog.objects.create(slug="author-test-blog", title="test-blog", owner=owner)
        blog.authors.add(owner)
        blog.authors.add(author)
        blog.save()
        Post.objects.create(slug="published-post" + "-" + hex(blog.id)[2:], title="published-post", is_published=True, blog=blog, author=author)
        Post.objects.create(slug="draft-post" + "-" + hex(blog.id)[2:], title="draft-post", is_published=False, blog=blog, author=author)

    @staticmethod
    def get_post_blog_users():
        return (
            Post.objects.get(slug="published-post" + "-" + hex(Blog.objects.get().id)[2:]),
            Post.objects.get(slug="draft-post" + "-" + hex(Blog.objects.get().id)[2:]),
            Blog.objects.get(),
            User.objects.get(username="stranger"),
            User.objects.get(username="author"),
            User.objects.get(username="owner"),
            User.objects.get(username="ADMIN")
        )

    @staticmethod
    def subtest_permission(client, auth_models, method, url, data=None):
        exact_responses = []
        for i in range(len(auth_models)):
            if auth_models[i] is not None:
                client.force_authenticate(user=auth_models[i])
            if method == "GET":
                exact_responses.append(client.get(url, data, format='json'))
            elif method == "POST":
                data["title"] = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
                exact_responses.append(client.post(url, data, format='json'))
            elif method == "POST-PUB":
                post = Post.objects.get(slug=data.get("slug"))
                response = client.post(url, format='json')
                if response.status_code == status.HTTP_204_NO_CONTENT:
                    post.is_published = False
                    post.save()
                exact_responses.append(response)
            elif method == "PUT":
                exact_responses.append(client.put(url, data, format='json'))
            elif method == "PATCH":
                exact_responses.append(client.patch(url, data, format='json'))
            elif method == "DELETE":
                exact_responses.append(client.delete(url, data, format='json'))
            elif method == "DELETE-REC":
                post = Post.objects.get(slug=data.get("slug"))
                response = client.delete(url, format='json')
                if response.status_code == status.HTTP_204_NO_CONTENT:
                    post.save()
                exact_responses.append(response)
        return exact_responses

    def test_list_post(self):
        pub_post, dr_post, blog, stranger, author, owner, admin = self.get_post_blog_users()
        url = reverse('post-list')
        auth_models = [None, stranger, author, owner, admin]
        expect_data_object_amount = [1, 1, 1, 1, 2]
        responses = self.subtest_permission(self.client, auth_models, "GET", url)
        self.assertEqual([obj.data.get("count") for obj in responses], expect_data_object_amount)

    def test_list_blog_post(self):
        pub_post, dr_post, blog, stranger, author, owner, admin = self.get_post_blog_users()
        url = reverse('blog-posts-list', kwargs={"slug": blog.slug})
        auth_models = [None, stranger, author, owner, admin]
        expect_data_object_amount = [1, 1, 1, 2, 2]
        responses = self.subtest_permission(self.client, auth_models, "GET", url)
        self.assertEqual([obj.data.get("count") for obj in responses], expect_data_object_amount)

    def test_create_post(self):
        pub_post, dr_post, blog, stranger, author, owner, admin = self.get_post_blog_users()
        url = reverse('post-list')
        data = {
            'title': 'test-post',
            'body': 'test post body',
            'tags': [],
            'blog_slug': blog.slug
        }
        auth_models = [None, stranger, author, owner, admin]
        expect_status = [status.HTTP_401_UNAUTHORIZED,
                         status.HTTP_403_FORBIDDEN,
                         status.HTTP_201_CREATED,
                         status.HTTP_201_CREATED,
                         status.HTTP_201_CREATED]
        responses = self.subtest_permission(self.client, auth_models, "POST", url, data)
        self.assertEqual([obj.status_code for obj in responses], expect_status)

    def test_update_post(self):
        pub_post, dr_post, blog, stranger, author, owner, admin = self.get_post_blog_users()
        url = reverse('post-detail', kwargs={"slug": pub_post.slug})
        data = {
            'title': pub_post.title,
            'body': 'test update body',
            'tags': [],
        }
        auth_models = [None, stranger, author, owner, admin]
        expect_status = [status.HTTP_401_UNAUTHORIZED,
                         status.HTTP_403_FORBIDDEN,
                         status.HTTP_200_OK,
                         status.HTTP_403_FORBIDDEN,
                         status.HTTP_200_OK]
        responses = self.subtest_permission(self.client, auth_models, "PUT", url, data)
        self.assertEqual([obj.status_code for obj in responses], expect_status)

    def test_partial_update_post(self):
        pub_post, dr_post, blog, stranger, author, owner, admin = self.get_post_blog_users()
        url = reverse('post-detail', kwargs={"slug": pub_post.slug})
        data = {
            'body': 'test partial update body',
        }
        auth_models = [None, stranger, author, owner, admin]
        expect_status = [status.HTTP_401_UNAUTHORIZED,
                         status.HTTP_403_FORBIDDEN,
                         status.HTTP_200_OK,
                         status.HTTP_403_FORBIDDEN,
                         status.HTTP_200_OK]
        responses = self.subtest_permission(self.client, auth_models, "PATCH", url, data)
        self.assertEqual([obj.status_code for obj in responses], expect_status)

    def test_delete_post(self):
        pub_post, dr_post, blog, stranger, author, owner, admin = self.get_post_blog_users()
        url = reverse('post-detail', kwargs={"slug": pub_post.slug})
        auth_models = [None, stranger, author, owner, admin]
        data = {
            'slug': pub_post.slug,
        }
        expect_status = [status.HTTP_401_UNAUTHORIZED,
                         status.HTTP_403_FORBIDDEN,
                         status.HTTP_204_NO_CONTENT,
                         status.HTTP_204_NO_CONTENT,
                         status.HTTP_204_NO_CONTENT]
        responses = self.subtest_permission(self.client, auth_models, "DELETE-REC", url, data)
        self.assertEqual([obj.status_code for obj in responses], expect_status)

    def test_publish_post(self):
        pub_post, dr_post, blog, stranger, author, owner, admin = self.get_post_blog_users()
        url = reverse('post-publish', kwargs={"slug": dr_post.slug})
        data = {
            'slug': dr_post.slug,
        }
        auth_models = [None, stranger, author, owner, admin]
        expect_status = [status.HTTP_401_UNAUTHORIZED,
                         status.HTTP_403_FORBIDDEN,
                         status.HTTP_204_NO_CONTENT,
                         status.HTTP_403_FORBIDDEN,
                         status.HTTP_204_NO_CONTENT]
        responses = self.subtest_permission(self.client, auth_models, "POST-PUB", url, data)
        self.assertEqual([obj.status_code for obj in responses], expect_status)
