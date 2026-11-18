# スナップ API と画像（作成・一覧・更新・削除・配信）

- 最終更新：2026-11-19（今の実装に合わせて書き直した。以前の「ファイルアップロード」「API 作成」の記事は git の履歴にある）
- 関連：[06_入力チェック.md](06_入力チェック.md)・[07_タグ.md](07_タグ.md)・[08_無限スクロール.md](08_無限スクロール.md)・[09_Zipダウンロード.md](09_Zipダウンロード.md)・[API 定義](../02_設計/api/index.yaml)

## 0. 全体の地図

| API | View（窓口） | Serializer（翻訳係） | Service・Signal（作業係） |
|---|---|---|---|
| `GET /chocolatier_api/snap/` | `SnapList` | `SnapSerializer` | ― |
| `POST /chocolatier_api/snap/create/` | `SnapCreate` | `SnapCreateSerializer` | `services/files.py` の `save_upload` |
| `GET /chocolatier_api/snap/{id}/` | `SnapDetail` | `SnapSerializer` | ― |
| `PATCH /chocolatier_api/snap/{id}/` | `SnapDetail` | `SnapUpdateSerializer` | `services/tags.py` |
| `DELETE /chocolatier_api/snap/{id}/` | `SnapDetail` | `SnapDeleteSerializer` | `signals.py` |
| `GET /media/{path}` | `MediaFileView` | ― | `services/files.py` の `full_path_of` |

- View は `backend/chocolatier_api/views/snap.py`・`views/media.py`、Serializer は `serializers/snap.py`。
- **持ち主だけ**：どの API も `Snap.objects.filter(user=request.user)` の範囲でしか探さない。他人の ID は 404（存在を知らせないため 403 にしない）。

## 1. データの形（models.py）
```python
class File(models.Model):        # 画像の情報（実体は media/uploads/ のファイル）
    name = models.CharField(max_length=255, blank=True, null=True)
    path = models.CharField(max_length=500, unique=True)  # uploads/元の名前_日時.拡張子

class Snap(models.Model):        # 投稿
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='snaps')
    file = models.ForeignKey('File', on_delete=models.CASCADE, related_name='snaps')
    comment = models.TextField(blank=True, null=True)
    tags = models.ManyToManyField('Tag', related_name='snaps', blank=True)
```
- スナップと画像は **1 対 1 が原則**（作成のたびに新しい File を作る）。DB は FK（多対 1）のままで、削除の後片付けでこの原則を守っている。
- 列の詳細は [DB 設計](../02_設計/db/tables.md)。

## 2. 作成（POST /chocolatier_api/snap/create/）
画面は multipart で `upload`（画像）・`comment`・`tags`（同じキーで繰り返す）を送る。

```python
class SnapCreate(generics.CreateAPIView):
    serializer_class = SnapCreateSerializer

    # 投稿者は送られた値ではなく、ログイン中の利用者にする（なりすまし防止）
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
```

```python
def create(self, validated_data):
    upload = validated_data.pop('upload')
    tag_names = validated_data.pop('tags', [])   # 多対多は create に渡せないので先に取り出す

    file_obj = None
    try:
        with transaction.atomic():                # ここからは 1 つの処理。失敗したら DB の変更を全部取り消す
            file_obj = save_upload(upload)        # ① 実ファイルを書いて File の行を作る
            snap = Snap.objects.create(file=file_obj, **validated_data)  # ② Snap
            set_snap_tags(snap, tag_names)        # ③ タグ（Snap の id ができてから）
    except Exception:
        if file_obj is not None:
            remove_physical_file(file_obj.path)   # ④ 実ファイルは DB ではないので、自分で消す
        raise
    return snap
```
| ポイント | 理由 |
|---|---|
| `transaction.atomic` | 途中で失敗したときに、File の行だけが残らないようにする（改修案件08） |
| 失敗したら実ファイルを消す | トランザクションは DB しか取り消さないため |
| 返す形は `SnapSerializer`（`to_representation`） | 画面が、返ってきたスナップをそのまま一覧に足せるように |

**画像の保存（services/files.py の `save_upload`）**
- 名前は `<元の名前>_<yyyymmddHHMMSS><拡張子>`、場所は `MEDIA_ROOT/uploads/`。`upload.chunks()` で少しずつ書く。
- DB への登録に失敗したら、書いた実ファイルを消す。
- 既知の不具合：同じ名前の画像を同じ秒に 2 回送ると、`path` の UNIQUE 制約で 500 になる（再現しにくいので今のまま）。

## 3. 一覧（GET /chocolatier_api/snap/）
```python
def get_queryset(self):
    queryset = (
        Snap.objects
        .filter(user=self.request.user)
        .select_related('file')    # 多対 1：JOIN でいっしょに取る
        .prefetch_related('tags')  # 多対多：別の SQL 1 回でまとめて取る（N+1 対策）
        .order_by('-created_at')
    )
    tag = self.request.query_params.get('tag')
    if tag:
        queryset = queryset.filter(tags__name=tag)
    return queryset
```
- 12 件ずつの cursor 方式（`pagination_class = SnapCursorPagination`）→ [08_無限スクロール.md](08_無限スクロール.md)
- 1 件の形：`{id, file, filePath, comment, tags, created_at, updated_at}`（`filePath` は `uploads/...`）

## 4. 更新（PATCH /chocolatier_api/snap/{id}/）
- 変えられるのはコメントとタグだけ（画像は変えられない）。JSON で送る。
- `tags` を送らなければタグはそのまま、`[]` を送ると全部外す（`pop('tags', None)` で区別）。
- **PUT は受け付けない**（405）。`SnapDetail.http_method_names = ['get', 'patch', 'delete', 'head', 'options']`。使っていないメソッドは開けておかない方針（改修案件08）。

## 5. 削除（DELETE /chocolatier_api/snap/{id}/）
```python
def destroy(self, request, *args, **kwargs):
    instance = self.get_object()            # 他人のスナップなら 404
    self.get_serializer(instance).delete(instance)
    return Response(status=status.HTTP_204_NO_CONTENT)  # 204 は本文なし
```
- 画像（File の行と実ファイル）と、使われなくなったタグの後片付けは **signals.py** が行う。

```python
@receiver(post_delete, sender=Snap)
def snap_deleted(sender, instance, **kwargs):
    File.objects.filter(id=instance.file_id).delete()  # ① 画像の行（→ 下の file_deleted が実ファイルを消す）
    delete_unused_tags()                                # ② どのスナップにも付いていないタグ

@receiver(post_delete, sender=File)
def file_deleted(sender, instance, **kwargs):
    remove_physical_file(instance.path)                 # 実ファイル（なければ何もしない）
```
| なぜシグナルか | |
|---|---|
| 以前 | 後片付けが API の削除の中にしかなく、管理画面や利用者の削除では実ファイルが残った |
| 今 | どこから消しても（API・管理画面・利用者の CASCADE）、Django が自動で呼ぶ |
| 登録 | `apps.py` の `ready()` で `signals.py` を読み込む（読み込まないと動かない） |
| 注意 | `instance.file` ではなく `instance.file_id` を使う（File の方が先に消えている場合があるため） |

## 6. 画像の配信（GET /media/{path}）
画面は `<img src={`${MEDIA_URL}${snap.filePath}`} />`（`MEDIA_URL` は `http://localhost:8000/media/`）で表示する。

```python
class MediaFileView(APIView):
    def get(self, request, file_path):
        # ① 自分のスナップの画像だけを DB から探す（Windows の「\」の形でも探す）
        file_obj = (
            File.objects
            .filter(path__in=[file_path, file_path.replace('/', '\\')], snaps__user=request.user)
            .first()
        )
        if file_obj is None:
            return Response({"detail": "見つかりませんでした。"}, status=404)
        # ② 実ファイルがなければ 404、あれば画像を返す（表示用なので as_attachment は付けない）
        ...
        return FileResponse(open(full_path, 'rb'), content_type=content_type)
```
| 状況 | 結果 |
|---|---|
| ログインした持ち主 | 200（画像） |
| 未ログイン | 401（共通設定のログイン必須） |
| 他人の画像・存在しない画像 | 404 |
| `/media/../manage.py` など | 404（DB に登録された path しか返さないので、別の場所のファイルは読めない） |

- ブラウザは `<img>` の取得にも Cookie（access_token）を付ける（`localhost:3000` と `:8000` は同じサイト）。画面側に特別な処理はいらない。
- 以前（改修案件08 より前）は Django の `static()` で配信していて、URL を知っていればログインなしで見られた。
- 注意：access_token（60 分）が切れると、画面が次の API 呼び出しで取り直すまで、新しい画像の取得は 401 になる。

## 7. テスト
| ファイル | 確かめていること |
|---|---|
| `tests/test_auth.py` の `PermissionTests` | 他人のスナップは 404、投稿者はログイン中の利用者 |
| `tests/test_snap.py` | 入力チェック・タグ・ページング |
| `tests/test_fixes.py` | PUT は 405・削除は本文なし・画像の配信・削除の後片付け・作成のトランザクション |
| `tests/test_services.py` | `save_upload`・`delete_file` を直接 |
