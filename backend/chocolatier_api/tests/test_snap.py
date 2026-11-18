# =========================================================
# tests/test_snap.py
# - 改修案件2：入力チェック
# - 改修案件3：タグ
# - 改修案件4：ページング（12 件ずつ・cursor 方式）
# =========================================================
import io
from urllib.parse import parse_qs, urlparse

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from ..models import Tag
from .base import BaseAPITestCase, make_image, tearDownModule  # noqa: F401


# =========================================================
# 改修案件2：入力チェック
# =========================================================
class ValidationTests(BaseAPITestCase):
    def test_png_can_be_uploaded(self):
        self.assertEqual(self.create_snap().status_code, 201)

    def test_image_over_5mb_returns_400(self):
        # 1500×1500 のランダムな色の PNG は、約 6.4MB になる
        big_image = make_image(size=(1500, 1500), random_pixels=True)
        self.assertGreater(big_image.size, 5 * 1024 * 1024)

        response = self.client.post('/chocolatier_api/snap/create/', {'upload': big_image}, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertIn('5MB', response.data['upload'][0])

    def test_text_file_with_png_extension_returns_400(self):
        # 中身がテキストの .png（Pillow が画像として読めない）
        fake = SimpleUploadedFile('fake.png', b'this is not an image', content_type='image/png')
        response = self.client.post('/chocolatier_api/snap/create/', {'upload': fake}, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertIn('upload', response.data)

    def test_bmp_returns_400(self):
        # 中身は本物の画像でも、許可していない拡張子は弾く
        buffer = io.BytesIO()
        Image.new('RGB', (2, 2)).save(buffer, 'BMP')
        bmp = SimpleUploadedFile('photo.bmp', buffer.getvalue(), content_type='image/bmp')
        response = self.client.post('/chocolatier_api/snap/create/', {'upload': bmp}, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertIn('bmp', response.data['upload'][0])

    def test_comment_over_1000_chars_returns_400(self):
        # 作成・更新の両方で弾く（片方だけだと、更新で 1001 文字にできてしまう）
        self.assertEqual(self.create_snap('あ' * 1000).status_code, 201)
        self.assertEqual(self.create_snap('あ' * 1001).status_code, 400)

        snap_id = self.create_snap().data['id']
        response = self.client.patch(f'/chocolatier_api/snap/{snap_id}/', {'comment': 'あ' * 1001}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('comment', response.data)


# =========================================================
# 改修案件3：タグ
# =========================================================
class TagTests(BaseAPITestCase):
    def test_create_with_tags(self):
        # multipart で同じキーを繰り返して送る → 名前順の配列で返る
        response = self.create_snap(tags=['旅行', 'カフェ'])
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['tags'], ['カフェ', '旅行'])

    def test_create_without_tags(self):
        response = self.create_snap()
        self.assertEqual(response.data['tags'], [])

    def test_tag_names_are_cleaned(self):
        # 前後の空白を取り、空のタグと重複は捨てる
        response = self.create_snap(tags=[' 旅行 ', '', '旅行', 'カフェ'])
        self.assertEqual(response.data['tags'], ['カフェ', '旅行'])

    def test_same_tag_name_is_shared(self):
        # alice と bob が同じ名前のタグを使っても、tags の表には 1 行だけ
        self.create_snap(tags=['旅行'])
        self.client.force_authenticate(self.bob)
        self.create_snap(tags=['旅行'])
        self.assertEqual(Tag.objects.filter(name='旅行').count(), 1)

    def test_too_many_tags_returns_400(self):
        self.assertEqual(self.create_snap(tags=[f'タグ{i}' for i in range(10)]).status_code, 201)
        response = self.create_snap(tags=[f'タグ{i}' for i in range(11)])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['tags'], ['タグは10個までにしてください'])

    def test_tag_over_30_chars_returns_400(self):
        self.assertEqual(self.create_snap(tags=['あ' * 30]).status_code, 201)
        response = self.create_snap(tags=['あ' * 31])
        self.assertEqual(response.status_code, 400)
        self.assertIn('30文字以内', response.data['tags'][0])

    def test_null_tag_returns_nested_error(self):
        # 要素ごとのエラーは {"tags": {0: [...]}} の入れ子になる（フロントの apiError.ts が対応している形）
        snap_id = self.create_snap().data['id']
        response = self.client.patch(f'/chocolatier_api/snap/{snap_id}/', {'tags': [None]}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn(0, response.data['tags'])

    def test_update_replaces_tags(self):
        snap_id = self.create_snap(tags=['旅行', 'カフェ']).data['id']
        url = f'/chocolatier_api/snap/{snap_id}/'

        # ① 送った内容に入れ替わる
        response = self.client.patch(url, {'tags': ['夜景']}, format='json')
        self.assertEqual(response.data['tags'], ['夜景'])
        # ② コメントだけ送ったときは、タグはそのまま
        response = self.client.patch(url, {'comment': 'コメントだけ'}, format='json')
        self.assertEqual(response.data['tags'], ['夜景'])
        # ③ 空の配列を送ると、全部外れる
        response = self.client.patch(url, {'tags': []}, format='json')
        self.assertEqual(response.data['tags'], [])

    def test_filter_by_tag(self):
        self.create_snap('京都', tags=['旅行'])
        self.create_snap('喫茶店', tags=['カフェ'])
        response = self.client.get('/chocolatier_api/snap/', {'tag': '旅行'})
        self.assertEqual([snap['comment'] for snap in response.data['results']], ['京都'])

    def test_tag_list_returns_only_own_tags(self):
        # ① alice は「旅行」を 2 回、「カフェ」を 1 回使う → 重複なし・名前順
        self.create_snap(tags=['旅行'])
        self.create_snap(tags=['旅行', 'カフェ'])
        # ② bob だけが使っているタグは、alice には見えない
        self.client.force_authenticate(self.bob)
        self.create_snap(tags=['bob のタグ'])

        self.client.force_authenticate(self.alice)
        self.assertEqual(self.client.get('/chocolatier_api/tags/').data, ['カフェ', '旅行'])

    def test_list_query_count_does_not_grow(self):
        # N+1 対策：件数が増えても、一覧の SQL の回数は変わらない
        for i in range(3):
            self.create_snap(tags=['旅行', f'タグ{i}'])
        with self.assertNumQueries(2):  # Snap と File を JOIN で 1 回 ＋ tags をまとめて 1 回
            self.client.get('/chocolatier_api/snap/')


# =========================================================
# 改修案件4：ページング（12 件ずつ・cursor 方式）
# =========================================================
class PaginationTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        # 14 件作る。偶数番目にだけ「旅行」タグを付ける（7 件）
        self.snap_ids = []
        for i in range(14):
            tags = ['旅行'] if i % 2 == 0 else []
            self.snap_ids.append(self.create_snap(str(i), tags=tags).data['id'])
        self.newest_first = self.snap_ids[::-1]

    def ids(self, response):
        return [snap['id'] for snap in response.data['results']]

    def test_first_page_has_12_newest_snaps(self):
        response = self.client.get('/chocolatier_api/snap/')
        self.assertEqual(set(response.data.keys()), {'next', 'previous', 'results'})
        self.assertEqual(self.ids(response), self.newest_first[:12])
        self.assertIn('cursor=', response.data['next'])
        self.assertIsNone(response.data['previous'])

    def test_next_page_has_the_rest(self):
        first = self.client.get('/chocolatier_api/snap/')
        second = self.client.get(first.data['next'])
        self.assertEqual(self.ids(second), self.newest_first[12:])
        self.assertIsNone(second.data['next'])  # 最後まで読んだ

    def test_no_duplicates_when_snap_is_added_while_reading(self):
        # 1 ページ目を読んだあとに新しい投稿が増えても、2 ページ目に重複や抜けがない
        first = self.client.get('/chocolatier_api/snap/')
        self.create_snap('途中で増えた投稿')
        second = self.client.get(first.data['next'])
        self.assertEqual(self.ids(first) + self.ids(second), self.newest_first)

    def test_tag_is_kept_in_next_url(self):
        # 絞り込みでも次のページがあるように、1 ページの件数を一時的に 2 件にする
        from ..pagination import SnapCursorPagination  # 「..」：tests/ の 1 つ上（chocolatier_api）
        original = SnapCursorPagination.page_size
        SnapCursorPagination.page_size = 2
        self.addCleanup(setattr, SnapCursorPagination, 'page_size', original)

        response = self.client.get('/chocolatier_api/snap/', {'tag': '旅行'})
        self.assertEqual(parse_qs(urlparse(response.data['next']).query)['tag'], ['旅行'])

        # 最後までたどると、タグ付きの 7 件が重複なく新しい順で取れる
        collected = self.ids(response)
        while response.data['next']:
            response = self.client.get(response.data['next'])
            collected += self.ids(response)
        tagged = [snap_id for i, snap_id in enumerate(self.snap_ids) if i % 2 == 0]
        self.assertEqual(collected, tagged[::-1])

    def test_invalid_cursor_returns_404(self):
        # 不正な cursor は、DRF が NotFound（404）として返す
        response = self.client.get('/chocolatier_api/snap/', {'cursor': 'invalid'})
        self.assertEqual(response.status_code, 404)
