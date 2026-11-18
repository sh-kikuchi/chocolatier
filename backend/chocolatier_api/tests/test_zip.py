# =========================================================
# tests/test_zip.py
# - 改修案件5：表示中の画像を Zip でダウンロード
# =========================================================
import io
import os
import zipfile

from ..models import Snap
from .base import TEMP_MEDIA_ROOT, BaseAPITestCase, tearDownModule  # noqa: F401


# =========================================================
# 改修案件5：表示中の画像を Zip でダウンロード
# =========================================================
class ZipDownloadTests(BaseAPITestCase):
    URL = '/chocolatier_api/snap/download/'

    # Zip ダウンロードの API を呼ぶ（tag を渡さなければ「すべて」）
    def download(self, ids, tag=None):
        data = {'ids': ids}
        if tag is not None:
            data['tag'] = tag
        return self.client.post(self.URL, data, format='json')

    # レスポンスの Zip を開いて、中のファイル名の一覧を返す
    # - FileResponse は少しずつ送る形（streaming_content）なので、つなげてから開く
    def zip_names(self, response):
        content = b''.join(response.streaming_content)
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            return sorted(zf.namelist())

    # 画像のファイル名（Zip の中で使われる名前）
    def file_name(self, snap_id):
        return os.path.basename(Snap.objects.get(id=snap_id).file.path.replace('\\', '/'))

    def test_zip_contains_images_in_tag_folder(self):
        # A1：自分の Snap 2 件 → 「旅行/」フォルダに 2 枚
        ids = [self.create_snap(tags=['旅行']).data['id'] for _ in range(2)]

        response = self.download(ids, tag='旅行')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/zip')
        # 日本語のファイル名は、エンコードされて filename* に入る（「旅行」→ %E6%97%85%E8%A1%8C）
        self.assertIn("filename*=utf-8''%E6%97%85%E8%A1%8C.zip", response['Content-Disposition'])
        self.assertEqual(self.zip_names(response), sorted(f'旅行/{self.file_name(i)}' for i in ids))

    def test_folder_is_subete_without_tag(self):
        # A2：tag を送らない → 「すべて/」フォルダ
        snap_id = self.create_snap().data['id']
        response = self.download([snap_id])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.zip_names(response), [f'すべて/{self.file_name(snap_id)}'])

    def test_other_users_snaps_are_excluded(self):
        # A3：bob の ID を混ぜても、bob の画像は入らない
        alice_id = self.create_snap().data['id']
        self.client.force_authenticate(self.bob)
        bob_id = self.create_snap().data['id']

        self.client.force_authenticate(self.alice)
        response = self.download([alice_id, bob_id])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.zip_names(response), [f'すべて/{self.file_name(alice_id)}'])

    def test_only_other_users_snaps_returns_404(self):
        # A4：bob の ID だけ・存在しない ID だけ → 404
        self.client.force_authenticate(self.bob)
        bob_id = self.create_snap().data['id']

        self.client.force_authenticate(self.alice)
        for ids in [[bob_id], [999999]]:
            with self.subTest(ids=ids):
                self.assertEqual(self.download(ids).status_code, 404)

    def test_over_100_ids_returns_400(self):
        # A5：100 件までは通る・101 件は 400
        # - 100 件の側は Snap を作らずに確かめる（存在しない ID なので 404 = チェックは通過した）
        self.assertEqual(self.download(list(range(1, 101))).status_code, 404)
        response = self.download(list(range(1, 102)))
        self.assertEqual(response.status_code, 400)
        self.assertIn('ids', response.data)

    def test_empty_or_missing_ids_returns_400(self):
        # A6：ids が空・未指定・数字でない → 400
        for data in [{'ids': []}, {}, {'ids': ['abc']}]:
            with self.subTest(data=data):
                response = self.client.post(self.URL, data, format='json')
                self.assertEqual(response.status_code, 400)
                self.assertIn('ids', response.data)

    def test_anonymous_returns_401(self):
        # A7：ログインしていない → 401
        snap_id = self.create_snap().data['id']
        self.client.force_authenticate(None)
        self.assertEqual(self.download([snap_id]).status_code, 401)

    def test_missing_file_is_skipped(self):
        # 実ファイルが消えている画像は飛ばして、残りだけを Zip にする
        ids = [self.create_snap().data['id'] for _ in range(2)]
        missing = Snap.objects.get(id=ids[0]).file.path.replace('\\', '/')
        os.remove(os.path.join(TEMP_MEDIA_ROOT, missing))

        response = self.download(ids)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.zip_names(response), [f'すべて/{self.file_name(ids[1])}'])

    def test_all_files_missing_returns_404(self):
        # 実ファイルが 1 枚もなければ、空の Zip ではなく 404
        snap_id = self.create_snap().data['id']
        path = Snap.objects.get(id=snap_id).file.path.replace('\\', '/')
        os.remove(os.path.join(TEMP_MEDIA_ROOT, path))
        self.assertEqual(self.download([snap_id]).status_code, 404)

    def test_unsafe_tag_is_cleaned_for_folder_name(self):
        # タグ名の記号は「_」に置き換える
        # - 「/」：Zip の中でフォルダが分かれてしまう
        # - 「..」：解凍したときに、展開先の外へファイルが出てしまう（Zip Slip）
        # - 記号と「.」を取って何も残らなければ「すべて」
        snap_id = self.create_snap().data['id']
        name = self.file_name(snap_id)
        cases = [
            ('旅行/2026', '旅行_2026'),
            ('../a', '_a'),
            ('..', 'すべて'),
            ('a:b*c?', 'a_b_c_'),
        ]
        for tag, folder in cases:
            with self.subTest(tag=tag):
                response = self.download([snap_id], tag=tag)
                self.assertEqual(self.zip_names(response), [f'{folder}/{name}'])
