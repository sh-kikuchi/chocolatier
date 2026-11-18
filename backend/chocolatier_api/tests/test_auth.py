# =========================================================
# tests/test_auth.py
# - 改修案件1：Cookie 認証・権限（ログイン必須・自分の Snap だけ）
# - 改修案件2：サインアップの権限（管理者だけ）
# =========================================================
from rest_framework.test import APIClient, APITestCase

from ..models import Snap, User
from .base import TEST_SETTINGS, BaseAPITestCase, make_image, tearDownModule  # noqa: F401（tearDownModule は unittest が名前で探すので、import しておく）


# =========================================================
# 改修案件1：Cookie 認証
# =========================================================
@TEST_SETTINGS
class CookieAuthTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', email='alice@example.com', password='alice-pass')

    def test_login_sets_httponly_cookies_and_hides_tokens(self):
        # ① ログインすると、access / refresh が HttpOnly の Cookie に入る
        response = self.client.post('/token/', {'username': 'alice', 'password': 'alice-pass'}, format='json')
        self.assertEqual(response.status_code, 200)
        for name in ['access_token', 'refresh_token']:
            self.assertIn(name, response.cookies)
            self.assertTrue(response.cookies[name]['httponly'])
        # ② レスポンス本文にはトークンを入れない（JS に渡さない）
        self.assertNotIn('access', response.data)
        self.assertNotIn('refresh', response.data)

    def test_login_with_wrong_password_returns_401(self):
        response = self.client.post('/token/', {'username': 'alice', 'password': 'wrong'}, format='json')
        self.assertEqual(response.status_code, 401)

    def test_cookie_is_sent_automatically_after_login(self):
        # ログインで受け取った Cookie を、テスト用のクライアントが次のリクエストで自動で送る
        self.client.post('/token/', {'username': 'alice', 'password': 'alice-pass'}, format='json')
        response = self.client.get('/chocolatier_api/user-info/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['username'], 'alice')

    def test_refresh_issues_new_access_cookie(self):
        self.client.post('/token/', {'username': 'alice', 'password': 'alice-pass'}, format='json')
        response = self.client.post('/token/refresh/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('access_token', response.cookies)

    def test_refresh_without_cookie_returns_401(self):
        response = self.client.post('/token/refresh/')
        self.assertEqual(response.status_code, 401)

    def test_logout_deletes_cookies(self):
        # Cookie の削除は「値を空にして、有効期限を 0 にする」形で返ってくる
        self.client.post('/token/', {'username': 'alice', 'password': 'alice-pass'}, format='json')
        response = self.client.post('/logout/')
        self.assertEqual(response.status_code, 200)
        for name in ['access_token', 'refresh_token']:
            self.assertEqual(response.cookies[name].value, '')
            self.assertEqual(response.cookies[name]['max-age'], 0)

    def test_post_without_csrf_token_returns_403(self):
        # enforce_csrf_checks=True：本物のブラウザと同じく CSRF をチェックする
        # （テスト用のクライアントは、ふだんは CSRF のチェックを省略している）
        client = APIClient(enforce_csrf_checks=True)
        client.post('/token/', {'username': 'alice', 'password': 'alice-pass'}, format='json')
        response = client.post('/chocolatier_api/snap/create/', {'upload': make_image()}, format='multipart')
        self.assertEqual(response.status_code, 403)

    def test_post_with_csrf_token_succeeds(self):
        # ① /csrf/ で csrftoken Cookie を受け取る
        client = APIClient(enforce_csrf_checks=True)
        client.get('/csrf/')
        client.post('/token/', {'username': 'alice', 'password': 'alice-pass'}, format='json')
        csrf_token = client.cookies['csrftoken'].value
        # ② 同じ値を X-CSRFToken ヘッダーにも付ける（フロントでは axios が自動で付ける）
        response = client.post(
            '/chocolatier_api/snap/create/',
            {'upload': make_image()},
            format='multipart',
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(response.status_code, 201)


# =========================================================
# 改修案件1：権限（ログイン必須・自分の Snap だけ）
# =========================================================
class PermissionTests(BaseAPITestCase):
    def test_anonymous_requests_return_401(self):
        self.client.force_authenticate(None)  # ログインしていない状態にする
        for url in ['/chocolatier_api/snap/', '/chocolatier_api/tags/', '/chocolatier_api/user-info/']:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 401)

    def test_list_returns_only_own_snaps(self):
        self.create_snap('alice の投稿')
        self.client.force_authenticate(self.bob)
        self.create_snap('bob の投稿')

        response = self.client.get('/chocolatier_api/snap/')
        comments = [snap['comment'] for snap in response.data['results']]
        self.assertEqual(comments, ['bob の投稿'])

    def test_other_users_snap_returns_404(self):
        # alice の Snap を、bob が取得・更新・削除しようとする → どれも 404
        snap_id = self.create_snap().data['id']
        self.client.force_authenticate(self.bob)
        url = f'/chocolatier_api/snap/{snap_id}/'

        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.patch(url, {'comment': '書き換え'}, format='json').status_code, 404)
        self.assertEqual(self.client.delete(url).status_code, 404)
        self.assertTrue(Snap.objects.filter(id=snap_id).exists())  # 消えていない

    def test_user_field_from_client_is_ignored(self):
        # なりすまし防止：user に bob の ID を送っても、投稿者はログインユーザー（alice）になる
        response = self.client.post(
            '/chocolatier_api/snap/create/',
            {'upload': make_image(), 'user': self.bob.id},
            format='multipart',
        )
        self.assertEqual(Snap.objects.get(id=response.data['id']).user, self.alice)

    def test_owner_can_update_and_delete(self):
        snap_id = self.create_snap().data['id']
        url = f'/chocolatier_api/snap/{snap_id}/'

        response = self.client.patch(url, {'comment': '更新しました'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['comment'], '更新しました')

        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertFalse(Snap.objects.filter(id=snap_id).exists())


# =========================================================
# 改修案件2：サインアップの権限
# =========================================================
class SignupPermissionTests(BaseAPITestCase):
    SIGNUP_DATA = {'username': 'carol', 'email': 'carol@example.com', 'password': 'carol-pass'}

    def test_anonymous_returns_401(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post('/chocolatier_api/signup/', self.SIGNUP_DATA, format='json').status_code, 401)

    def test_general_user_returns_403(self):
        # alice は一般ユーザー（is_staff=False）
        self.assertEqual(self.client.post('/chocolatier_api/signup/', self.SIGNUP_DATA, format='json').status_code, 403)

    def test_admin_can_signup(self):
        admin = User.objects.create_user(username='admin', email='admin@example.com', password='admin-pass', is_staff=True)
        self.client.force_authenticate(admin)
        response = self.client.post('/chocolatier_api/signup/', self.SIGNUP_DATA, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertFalse(User.objects.get(username='carol').is_staff)  # 作られるのは一般ユーザー
