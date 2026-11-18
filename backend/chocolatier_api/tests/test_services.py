# =========================================================
# tests/test_services.py
# - 改修案件7：services/（作業係）の単体テスト
# - API（URL・ログイン・Response）を通さず、関数を直接呼んで確かめる
#   → 作業係が HTTP を知らない作りになっていることの確認にもなる
# =========================================================
import os
import zipfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase

from ..models import File, Snap
from ..services.files import delete_file, save_upload
from ..services.zip import build_snap_zip, safe_folder_name
from .base import TEMP_MEDIA_ROOT, TEST_SETTINGS, BaseAPITestCase, tearDownModule  # noqa: F401


# ---------------------------------------------------------
# safe_folder_name：DB もファイルも使わないので SimpleTestCase（DB を用意しないぶん速い）
# ---------------------------------------------------------
class SafeFolderNameTests(SimpleTestCase):
    def test_folder_names(self):
        cases = [
            ('旅行', '旅行'),            # そのまま
            (None, 'すべて'),           # 「すべて」のときは tag なし
            ('', 'すべて'),
            ('旅行/2026', '旅行_2026'),  # 「/」で Zip の中のフォルダが分かれないように
            ('../a', '_a'),             # 解凍先の外に出ないように（Zip Slip）
            ('..', 'すべて'),           # 記号と「.」を取って何も残らない
            (' 旅行 ', '旅行'),          # 前後の空白
            ('a:b*c?', 'a_b_c_'),       # Windows でフォルダ名に使えない記号
        ]
        for tag, expected in cases:
            with self.subTest(tag=tag):
                self.assertEqual(safe_folder_name(tag), expected)


# ---------------------------------------------------------
# build_snap_zip：Snap を API で作ってから、関数を直接呼ぶ
# ---------------------------------------------------------
class BuildSnapZipTests(BaseAPITestCase):
    def snaps(self, ids):
        return Snap.objects.filter(id__in=ids).select_related('file').order_by('-created_at')

    def test_returns_zip_from_start_and_count(self):
        # ① 2 枚入り、読む位置が先頭に戻っている（そのまま読める）
        ids = [self.create_snap().data['id'] for _ in range(2)]
        zip_file, added = build_snap_zip(self.snaps(ids), '旅行')
        self.addCleanup(zip_file.close)

        self.assertEqual(added, 2)
        self.assertEqual(zip_file.tell(), 0)
        with zipfile.ZipFile(zip_file) as zf:
            names = zf.namelist()
        self.assertEqual(len(names), 2)
        self.assertTrue(all(name.startswith('旅行/') for name in names))

    def test_missing_files_are_counted_as_zero(self):
        # ② 実ファイルがなければ 0 枚（404 にするかどうかは View が決める）
        snap_id = self.create_snap().data['id']
        path = Snap.objects.get(id=snap_id).file.path.replace('\\', '/')
        os.remove(os.path.join(TEMP_MEDIA_ROOT, path))

        zip_file, added = build_snap_zip(self.snaps([snap_id]), 'すべて')
        self.addCleanup(zip_file.close)
        self.assertEqual(added, 0)


# ---------------------------------------------------------
# save_upload / delete_file：実ファイルと File（DB の行）がそろって作られ・消えること
# ---------------------------------------------------------
@TEST_SETTINGS
class FilesServiceTests(TestCase):
    def test_save_then_delete(self):
        # ① 保存：uploads/<元の名前>_<日時>.png に書き込まれ、File が 1 行できる
        upload = SimpleUploadedFile('service_test.png', b'dummy-bytes', content_type='image/png')
        file_obj = save_upload(upload)
        full_path = os.path.join(TEMP_MEDIA_ROOT, file_obj.path.replace('\\', '/'))

        self.assertRegex(file_obj.path.replace('\\', '/'), r'^uploads/service_test_\d{14}\.png$')
        self.assertEqual(file_obj.name, os.path.basename(full_path))
        self.assertTrue(os.path.exists(full_path))
        with open(full_path, 'rb') as f:
            self.assertEqual(f.read(), b'dummy-bytes')

        # ② 削除：実ファイルと DB の行の両方が消える
        delete_file(file_obj)
        self.assertFalse(os.path.exists(full_path))
        self.assertFalse(File.objects.filter(id=file_obj.id).exists())

    def test_delete_none_does_nothing(self):
        # ③ None を渡してもエラーにならない
        delete_file(None)
