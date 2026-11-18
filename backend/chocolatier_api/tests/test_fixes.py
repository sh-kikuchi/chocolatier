# =========================================================
# tests/test_fixes.py
# - 改修案件08：調査で見つかった指摘（Q-008〜Q-020）への対応のテスト
# =========================================================
import os
import re
from pathlib import Path
from unittest import mock

from django.conf import settings

from ..models import File, Snap, Tag, User
from .base import TEMP_MEDIA_ROOT, BaseAPITestCase, tearDownModule  # noqa: F401


# 実ファイルの場所（DB の path から作る）
def full_path(file_obj):
    return os.path.join(TEMP_MEDIA_ROOT, file_obj.path.replace('\\', '/'))


# =========================================================
# Q-008・Q-018：スナップの詳細 API
# =========================================================
class SnapDetailMethodTests(BaseAPITestCase):
    def test_put_is_not_allowed(self):
        # Q-008：画面で使っていない PUT は受け付けない（405）。PATCH は今までどおり使える
        snap_id = self.create_snap().data['id']
        url = f'/chocolatier_api/snap/{snap_id}/'
        self.assertEqual(self.client.put(url, {'comment': '置き換え'}, format='json').status_code, 405)
        self.assertEqual(self.client.patch(url, {'comment': '更新'}, format='json').status_code, 200)

    def test_delete_returns_204_without_body(self):
        # Q-018：削除の 204 には本文を付けない
        snap_id = self.create_snap().data['id']
        response = self.client.delete(f'/chocolatier_api/snap/{snap_id}/')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b'')


# =========================================================
# Q-009：画像はログインしている持ち主にだけ見せる
# =========================================================
class MediaAccessTests(BaseAPITestCase):
    def url(self, snap_id):
        return '/media/' + Snap.objects.get(id=snap_id).file.path.replace('\\', '/')

    def test_owner_can_see_image(self):
        snap_id = self.create_snap().data['id']
        response = self.client.get(self.url(snap_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertTrue(b''.join(response.streaming_content).startswith(b'\x89PNG'))

    def test_anonymous_returns_401(self):
        snap_id = self.create_snap().data['id']
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url(snap_id)).status_code, 401)

    def test_other_user_and_unknown_return_404(self):
        # 他人の画像も、存在しない画像も同じ 404（存在すること自体を知らせない）
        snap_id = self.create_snap().data['id']
        url = self.url(snap_id)
        self.client.force_authenticate(self.bob)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_authenticate(self.alice)
        self.assertEqual(self.client.get('/media/uploads/nothing.png').status_code, 404)
        self.assertEqual(self.client.get('/media/../manage.py').status_code, 404)


# =========================================================
# Q-011・Q-012：どこから消しても、画像（File の行と実ファイル）が残らない
# =========================================================
class DeleteCleanupTests(BaseAPITestCase):
    def make(self):
        snap = Snap.objects.get(id=self.create_snap().data['id'])
        return snap, snap.file, full_path(snap.file)

    def test_api_delete_removes_file(self):
        snap, file_obj, path = self.make()
        self.client.delete(f'/chocolatier_api/snap/{snap.id}/')
        self.assertFalse(File.objects.filter(id=file_obj.id).exists())
        self.assertFalse(os.path.exists(path))

    def test_deleting_snap_directly_removes_file(self):
        # 管理画面からスナップを消したとき（＝モデルの delete）
        snap, file_obj, path = self.make()
        snap.delete()
        self.assertFalse(File.objects.filter(id=file_obj.id).exists())
        self.assertFalse(os.path.exists(path))

    def test_deleting_file_removes_snap_and_physical_file(self):
        # 管理画面から File を消したとき（CASCADE でスナップも消える）
        snap, file_obj, path = self.make()
        file_obj.delete()
        self.assertFalse(Snap.objects.filter(id=snap.id).exists())
        self.assertFalse(os.path.exists(path))

    def test_deleting_user_removes_files(self):
        # 利用者を消したとき（CASCADE でスナップが消え、画像も消える）
        snap, file_obj, path = self.make()
        self.alice.delete()
        self.assertFalse(File.objects.filter(id=file_obj.id).exists())
        self.assertFalse(os.path.exists(path))


# =========================================================
# Q-014：どのスナップにも付いていないタグは消す
# =========================================================
class UnusedTagTests(BaseAPITestCase):
    def test_tag_is_deleted_when_no_snap_uses_it(self):
        snap_id = self.create_snap(tags=['旅行', 'カフェ']).data['id']
        self.client.patch(f'/chocolatier_api/snap/{snap_id}/', {'tags': ['旅行']}, format='json')
        self.assertFalse(Tag.objects.filter(name='カフェ').exists())
        self.assertTrue(Tag.objects.filter(name='旅行').exists())

    def test_tag_used_by_other_user_is_kept(self):
        # タグは全利用者で共通。bob が使っていれば、alice が外しても消えない
        snap_id = self.create_snap(tags=['旅行']).data['id']
        self.client.force_authenticate(self.bob)
        self.create_snap(tags=['旅行'])
        self.client.force_authenticate(self.alice)
        self.client.patch(f'/chocolatier_api/snap/{snap_id}/', {'tags': []}, format='json')
        self.assertTrue(Tag.objects.filter(name='旅行').exists())

    def test_tag_is_deleted_with_last_snap(self):
        snap_id = self.create_snap(tags=['夜景']).data['id']
        self.client.delete(f'/chocolatier_api/snap/{snap_id}/')
        self.assertFalse(Tag.objects.filter(name='夜景').exists())


# =========================================================
# Q-017：作成の途中で失敗したら、何も残さない
# =========================================================
class CreateTransactionTests(BaseAPITestCase):
    def test_failure_leaves_no_rows_and_no_file(self):
        uploads = Path(TEMP_MEDIA_ROOT) / 'uploads'
        before = set(uploads.glob('*')) if uploads.exists() else set()
        # タグ付けの段階でわざと失敗させる（画像の保存と Snap の作成は済んだあと）
        with mock.patch('chocolatier_api.serializers.snap.set_snap_tags', side_effect=RuntimeError('わざと失敗')):
            with self.assertRaises(RuntimeError):
                self.create_snap(tags=['旅行'])
        self.assertEqual(Snap.objects.count(), 0)
        self.assertEqual(File.objects.count(), 0)
        after = set(uploads.glob('*')) if uploads.exists() else set()
        self.assertEqual(after, before)


# =========================================================
# Q-013：メールアドレスの重複は登録できない（空なら重複を見ない）
# =========================================================
class SignupEmailTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        admin = User.objects.create_user(username='admin', email='admin@example.com', password='admin-pass', is_staff=True)
        self.client.force_authenticate(admin)

    def signup(self, username, email):
        return self.client.post('/chocolatier_api/signup/', {'username': username, 'email': email, 'password': 'pass-1234'}, format='json')

    def test_duplicate_email_returns_400(self):
        # alice@example.com は BaseAPITestCase で作成済み。大文字・小文字の違いも同じとみなす
        response = self.signup('alice2', 'Alice@Example.com')
        self.assertEqual(response.status_code, 400)
        self.assertIn('email', response.data)

    def test_blank_email_can_be_used_twice(self):
        self.assertEqual(self.signup('carol', '').status_code, 201)
        self.assertEqual(self.signup('dave', '').status_code, 201)


# =========================================================
# Q-020：Frontend と Backend の上限値が同じか（ずれたらこのテストが失敗する）
# - Frontend の src/utils/validators.ts を読んで、settings.py の値と比べる
# =========================================================
class LimitsSyncTests(BaseAPITestCase):
    VALIDATORS = Path(settings.BASE_DIR).parent / 'frontend' / 'src' / 'utils' / 'validators.ts'

    def read_const(self, source, name):
        match = re.search(rf'export const {name} = (.+?);', source)
        self.assertIsNotNone(match, f'{name} が validators.ts に見つからない')
        return match.group(1)

    def test_frontend_limits_match_backend(self):
        if not self.VALIDATORS.exists():
            self.skipTest('frontend がない環境では比べない')
        source = self.VALIDATORS.read_text(encoding='utf-8')
        # 数値の定数：「5 * 1024 * 1024」のような掛け算も計算して比べる
        for name in ['MAX_UPLOAD_SIZE', 'MAX_COMMENT_LENGTH', 'MAX_TAGS_PER_SNAP', 'MAX_TAG_LENGTH', 'MAX_ZIP_DOWNLOAD']:
            with self.subTest(name=name):
                expr = self.read_const(source, name)
                self.assertRegex(expr, r'^[\d\s*]+$')
                value = 1
                for part in expr.split('*'):
                    value *= int(part)
                self.assertEqual(value, getattr(settings, name))
        # 拡張子の一覧
        exts = re.findall(r"'([a-z]+)'", self.read_const(source, 'ALLOWED_IMAGE_EXTENSIONS'))
        self.assertEqual(exts, settings.ALLOWED_IMAGE_EXTENSIONS)
