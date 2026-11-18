# =========================================================
# tests/base.py
# - テストの共通部品（設定・画像の作り方・ログイン済みの準備）
# - ファイル名が test_ で始まらないので、このファイル自体はテストとして実行されない
# =========================================================
import io
import os
import shutil
import tempfile
from itertools import count

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from rest_framework.test import APITestCase

from ..models import User

# アップロード画像の保存先（テスト用の一時フォルダ）
TEMP_MEDIA_ROOT = tempfile.mkdtemp()

# ファイル名の連番
# - 同じ名前の画像を同じ秒に 2 回アップロードすると、File.path の一意制約で 500 になる（既知の不具合）
# - テストでは毎回違う名前にして避ける
_file_number = count()


# テスト用の設定
# - MEDIA_ROOT：アップロード画像を一時フォルダに保存する
# - PASSWORD_HASHERS：パスワードのハッシュ化を軽いものにして、テストを速くする
#   （本物のハッシュ化は、わざと時間がかかるように作られているため。テストの中だけの設定）
TEST_SETTINGS = override_settings(
    MEDIA_ROOT=TEMP_MEDIA_ROOT,
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
)


# テストのファイル（test_*.py）1 つ分が終わったら、一時フォルダを消す
# - unittest は、各テストファイルの中にある「tearDownModule」という名前の関数を探して呼ぶ
#   → 各テストファイルで `from .base import tearDownModule` しておく
# - 次のテストファイルで画像を保存するときは、保存処理（os.makedirs）がフォルダを作り直す
def tearDownModule():
    shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)


def make_image(size=(2, 2), random_pixels=False):
    # ① テスト用の PNG 画像を作る
    #    - random_pixels=True：ランダムな色で埋める（PNG は圧縮が効かず、ファイルが大きくなる）
    if random_pixels:
        image = Image.frombytes('RGB', size, os.urandom(size[0] * size[1] * 3))
    else:
        image = Image.new('RGB', size, 'white')
    buffer = io.BytesIO()
    image.save(buffer, 'PNG')
    # ② アップロードされたファイルの形にする
    return SimpleUploadedFile(f'test{next(_file_number)}.png', buffer.getvalue(), content_type='image/png')


# ---------------------------------------------------------
# BaseAPITestCase：Snap を扱うテストの共通の準備
# - alice と bob の 2 人を作り、alice でログインした状態から始める
# - force_authenticate：Cookie のログインを省略して「alice としてリクエストする」
#   （Cookie 認証そのものは test_auth.py の CookieAuthTests で確かめる）
# ---------------------------------------------------------
@TEST_SETTINGS
class BaseAPITestCase(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username='alice', email='alice@example.com', password='alice-pass')
        self.bob = User.objects.create_user(username='bob', email='bob@example.com', password='bob-pass')
        self.client.force_authenticate(self.alice)

    # Snap を API で作る（multipart）。tags は同じキーで繰り返し送られる
    def create_snap(self, comment='テスト', tags=None):
        data = {'comment': comment, 'upload': make_image()}
        if tags is not None:
            data['tags'] = tags
        return self.client.post('/chocolatier_api/snap/create/', data, format='multipart')
