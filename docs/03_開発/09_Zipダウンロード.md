# 表示中の画像を Zip でダウンロード

- 最終更新：2026-11-19（改修案件7 で、フォルダ名の安全化と Zip の作成を `services/zip.py`（作業係）に移した。View は流れだけを持つ）

- 改修案件5で、Snap 一覧に表示している画像（絞り込み中のタグ＋スクロールで読み込んだ分、最大 100 枚）を、Zip にまとめてダウンロードできるようにした。

- Zip を作るのは Backend（Python 標準の `zipfile`）、Frontend は ID を送って、返ってきた Zip を保存させるだけ。

- 改修の記録（計画からの変更点・確認結果）は [04\_改修事案/05\_表示中の画像Zipダウンロード.md](../04_改修事案/05_表示中の画像Zipダウンロード.md)。

- API の仕様は [02\_設計/api/index.yaml](../02_設計/api/index.yaml) の `POST /chocolatier_api/snap/download/`。

- [表示中の画像を Zip でダウンロード](#表示中の画像を-zip-でダウンロード)
  - [0. 考え方](#0-考え方)
    - [■ 全体の流れ](#-全体の流れ)
    - [■ 「表示しているもの」を対象にした理由](#-表示しているものを対象にした理由)
    - [■ Zip を Backend で作る理由](#-zip-を-backend-で作る理由)
  - [1. Backend](#1-backend)
    - [■ 受け取る値のチェック(serializers/snap.py)](#-受け取る値のチェックserializerssnappy)
    - [■ ID を信用しない(views/snap.py ②)](#-id-を信用しないviewssnappy-)
    - [■ フォルダ名を安全にする(services/zip.py の safe_folder_name)](#-フォルダ名を安全にするserviceszippy-の-safe_folder_name)
    - [■ Zip を一時ファイルに書き込む(services/zip.py の build_snap_zip)](#-zip-を一時ファイルに書き込むserviceszippy-の-build_snap_zip)
    - [■ FileResponse で返す(views/snap.py ⑥)](#-fileresponse-で返すviewssnappy-)
  - [2. Frontend](#2-frontend)
    - [■ Blob で受け取る](#-blob-で受け取る)
    - [■ ブラウザに保存させる](#-ブラウザに保存させる)
    - [■ エラーも Blob で届く(apiError.ts)](#-エラーも-blob-で届くapierrorts)
    - [■ ボタンの見せ方](#-ボタンの見せ方)
  - [3. テスト手順](#3-テスト手順)
  - [4. つまずきやすいところ](#4-つまずきやすいところ)

## 0\. 考え方

### ■ 全体の流れ

```
Frontend（SnapshotPage）                         Backend（SnapZipDownload）
① 表示中の snaps から ID を集める（新しい順に 100 件まで）
② POST /chocolatier_api/snap/download/
   { ids: [12, 11, ...], tag: "旅行" }  ───────▶ ③ 値をチェック（Serializer）
                                                  ④ 自分の Snap だけに絞る
                                                  ⑤ 一時ファイルに Zip を書き込む
                                                     旅行/photo_2026....jpg
   ⑦ Blob で受け取る  ◀─────────────────────── ⑥ FileResponse で返す
⑧ <a download="旅行.zip"> をクリックして保存
```

### ■ 「表示しているもの」を対象にした理由

| 観点 | 内容 |
|---|---|
| わかりやすさ | 画面で見えている写真が、そのまま Zip に入る（見たまま） |
| 量の制御 | 一覧は 12 件ずつしか読み込まれないので、ユーザーがスクロールした分しか増えない。さらに 100 枚で止めるので、Zip は最大でも約 500MB（1 枚 5MB × 100） |
| 「すべて」の扱い | タグごとにフォルダを分けると、タグなしの画像や複数のタグが付いた画像の置き場所に困る。表示中の分を 1 つのフォルダにまとめれば、この問題が起きない |

### ■ Zip を Backend で作る理由

- 画像の実ファイルはサーバーの `media/uploads/` にある。Backend なら、ファイルを読んでそのまま Zip に入れられる。
- Frontend で作ると、画像を 1 枚ずつダウンロードしてからまとめることになり、通信が増えるうえにライブラリも必要になる。

* * *

## 1\. Backend

### ■ 受け取る値のチェック(serializers/snap.py)

```python
class SnapZipDownloadSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=settings.MAX_ZIP_DOWNLOAD,  # 100
    )
    tag = serializers.CharField(required=False, max_length=settings.MAX_TAG_LENGTH)
```

- DB に保存しない「チェックするだけ」の役なので、`ModelSerializer` ではなく **`Serializer`** を使う。

|  | ModelSerializer（SnapCreateSerializer など） | Serializer（今回） |
|---|---|---|
| フィールド | `Meta.fields` に名前を並べると、モデルから自動で作られる | 自分で `ids = serializers.ListField(...)` と宣言する |
| オプション | `extra_kwargs` で足す | 宣言するときの引数に直接書く |
| 保存 | `create()` / `update()` で DB に保存する | しない |

- View では `serializer.is_valid(raise_exception=True)` と書く。エラーがあれば、DRF が自動で 400 を返してくれる。

### ■ ID を信用しない(views/snap.py ②)

```python
snaps = (
    Snap.objects
    .filter(user=request.user, id__in=ids)
    .select_related('file')
    .order_by('-created_at')
)
```

- `ids` は Frontend から送られてくるので、開発者ツールなどで **書き換えられる前提** で扱う。
- `user=request.user` で絞れば、他人の ID が混ざっていても黙って除外される。他人の ID だけなら 0 件 → 404。
- `id__in=ids`：「`ids` の配列に含まれる ID」という条件（`__in` は SQL の `IN`）。

### ■ フォルダ名を安全にする(services/zip.py の safe_folder_name)

```python
def safe_folder_name(tag):
    safe_tag = re.sub(r'[\\/:*?"<>|]', '_', tag or '').strip(' .')
    return safe_tag or 'すべて'
```

- タグ名には記号の制限がないので、`旅行/2026` や `../a` のようなタグも作れる。
- そのままフォルダ名にすると：
    - `/` → Zip の中でフォルダが分かれてしまう（`旅行` の中に `2026`）
    - `..` → 解凍したときに、展開先の **1 つ上のフォルダ** にファイルが出てしまう恐れがある（**Zip Slip** と呼ばれる問題）
- 記号は `_` に置き換え、前後の空白と `.` を取る。何も残らなければ `すべて`。

### ■ Zip を一時ファイルに書き込む(services/zip.py の build_snap_zip)

```python
def build_snap_zip(snaps, folder_name):
    zip_file = tempfile.TemporaryFile()
    added = 0
    with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_STORED) as zf:
        for snap in snaps:
            full_path = os.path.join(settings.MEDIA_ROOT, snap.file.path.replace('\\', '/'))
            if not os.path.exists(full_path):
                continue
            zf.write(full_path, arcname=f'{folder_name}/{os.path.basename(full_path)}')
            added += 1
    zip_file.seek(0)          # 読む位置を先頭に戻してから返す
    return zip_file, added    # 404 にするかどうかは View が added を見て決める
```

- 作業係（Service）は HTTP を知らない作りにしている（`request`・`Response`・ステータスコードを使わない）。だから API を通さずに単独でテストできる（`tests/test_services.py`）。

| 道具 | 役割 |
|---|---|
| `tempfile.TemporaryFile()` | 閉じると自動で消える一時ファイル。最大 500MB になりうるので、メモリではなくファイルに書く |
| `zipfile.ZipFile(..., 'w', ZIP_STORED)` | Zip を作る。`ZIP_STORED` は「圧縮しない」。JPEG / PNG はもともと圧縮済みなので、圧縮しても CPU を使うだけでほぼ小さくならない |
| `arcname` | **Zip の中での名前**。指定しないと `C:\Users\...` の長いパスがそのままフォルダとして入ってしまう |

- 一時ファイルは `with` で開かない。`with` を抜けると閉じて消えてしまい、返す前になくなるため。
- 実ファイルが消えている画像は飛ばす。1 枚も入らなければ、空の Zip ではなく 404 を返す。

### ■ FileResponse で返す(views/snap.py ⑥)

```python
folder_name = safe_folder_name(tag)
zip_file, added = build_snap_zip(snaps, folder_name)
if added == 0:
    zip_file.close()
    return Response({"detail": "ダウンロードできる画像がありません"}, status=status.HTTP_404_NOT_FOUND)
return FileResponse(
    zip_file,
    as_attachment=True,
    filename=f'{folder_name}.zip',
    content_type='application/zip',
)
```

- **`seek(0)` を忘れない**（`build_snap_zip` の中で済ませている）。書き込んだ直後は、読む位置がファイルの最後にある。そのまま返すと **空の Zip** になる。
- `as_attachment=True`：ブラウザに「表示」ではなく「保存」させる（`Content-Disposition: attachment`）。
- `filename`：日本語でも Django が自動でエンコードする（`filename*=utf-8''%E6%97%85%E8%A1%8C.zip`）。
- 送り終わると `FileResponse` がファイルを閉じる → 一時ファイルも自動で消える。

* * *

## 2\. Frontend

### ■ Blob で受け取る

```ts
const response = await client.post<Blob>(
  '/chocolatier_api/snap/download/',
  selectedTag ? { ids, tag: selectedTag } : { ids },
  { responseType: 'blob' }
);
```

- **`responseType: 'blob'`** を付けないと、axios が中身を文字として読もうとして Zip が壊れる。
- Blob は「名前のないデータのかたまり」。画像のトリミング（改修案件6）で作る File は「名前の付いた Blob」。

### ■ ブラウザに保存させる

```ts
const url = URL.createObjectURL(response.data);  // ① Blob に一時的な URL を付ける
const link = document.createElement('a');         // ② <a> を JS で作る
link.href = url;
link.download = `${folderName}.zip`;              // ③ 保存するときの名前
document.body.appendChild(link);                  //    ブラウザによっては、ページに置かないと click が効かない
link.click();                                     // ④ クリックしたことにする → 保存される
link.remove();
URL.revokeObjectURL(url);                         // ⑤ 一時的な URL を破棄する
```

- ファイル名は Frontend で決める。サーバーの `Content-Disposition` ヘッダーは、CORS の設定（`Access-Control-Expose-Headers`）を足さないと JS から読めないため。

### ■ エラーも Blob で届く(apiError.ts)

```ts
export const getApiErrorMessagesFromBlob = async (error: unknown): Promise<string[]> => {
  if (axios.isAxiosError(error) && error.response?.data instanceof Blob) {
    try {
      error.response.data = JSON.parse(await error.response.data.text());  // Blob → 文字 → オブジェクト
    } catch {
      error.response.data = null;  // JSON でない本文（500 の HTML など）は捨てる
    }
  }
  return getApiErrorMessages(error);
};
```

- `responseType: 'blob'` で呼ぶと、**エラーのときの本文（`{"detail": "..."}`）も Blob** で届く。
- そのまま今までの `getApiErrorMessages` に渡すと、中身を読めない。文字にして JSON に戻してから渡す。
- Blob を読むのは非同期なので、この関数も `async`（呼ぶ側は `await`）。

### ■ ボタンの見せ方

- 1 段目の右端に置く。文字に **選んでいるタグ名と枚数** を入れる（例：「いぬ」の 12 枚を Zip でダウンロード）。
    - タグを切り替えたり、スクロールで続きを読み込んだりすると、文字が変わる → 「表示中のものが対象」だと伝わる
- 100 枚を超えたら、ボタンの横に「表示中の 108 枚のうち、新しい 100 枚まで」と先に知らせる。
- ダウンロード中・0 件のときは押せない（`BasicButton` に `disabled` を追加した）。

* * *

## 3\. テスト手順

**自動テスト**（`backend` フォルダで、venv を有効にしてから）

```
python manage.py test chocolatier_api
```

`ZipDownloadTests` で次を確かめている。

| 内容 | 期待 |
|---|---|
| 自分の Snap 2 件＋`tag: 旅行` | 200。`旅行.zip` の中の `旅行/` に 2 枚 |
| `tag` なし | フォルダ名が `すべて/` |
| 他人の ID を混ぜる | 他人の画像は入らない |
| 他人の ID だけ・存在しない ID だけ | 404 |
| 100 件は通る・101 件 | 400 |
| `ids` が空・未指定・数字でない | 400 |
| 未ログイン | 401 |
| 実ファイルが 1 枚消えている／全部消えている | 飛ばす／404 |
| タグ名に `/` `..` `:` など | `_` に置き換わる。何も残らなければ `すべて/` |

テストでは、Zip を開いて中のファイル名まで確かめている（`zipfile.ZipFile(io.BytesIO(...)).namelist()`）。`FileResponse` は少しずつ送る形なので、`b''.join(response.streaming_content)` でつなげてから開く。

**ブラウザ確認**

1. タグを選んで押す → `<タグ名>.zip` が保存され、中に表示中の画像が入っている
2. 「すべて」で押す → `すべて.zip`
3. 押した瞬間に「Zip を作成中...」になり、押せなくなる

* * *

## 4\. つまずきやすいところ

| 症状 | 原因 | 対処 |
|---|---|---|
| ダウンロードした Zip が空・壊れている | `seek(0)` を忘れた | 返す前に `zip_file.seek(0)` |
| 返す前にファイルが消える | 一時ファイルを `with tempfile.TemporaryFile()` で開いた | `with` を使わず、閉じるのは `FileResponse` に任せる |
| Zip の中に `C:\Users\...` のフォルダができる | `arcname` を指定していない | `arcname=f'{フォルダ名}/{ファイル名}'` |
| Frontend で Zip が壊れる | `responseType: 'blob'` を付けていない | 付ける |
| エラーが「エラーが発生しました」としか出ない | エラーの本文が Blob のまま | `getApiErrorMessagesFromBlob` で読んでから変換する |
| `NameError` / `TypeError` が呼んだときだけ出る | Serializer の import 漏れ、`raise_exception` のスペルミス | `manage.py check` は View の中身までは実行しないので、テストか実際の呼び出しで確かめる |
| `ModuleNotFoundError: No module named 'corsheaders'` | venv を有効にしていない | `.\venv\Scripts\Activate.ps1` してから実行する |
| 件数のエラーが英語 | DRF に `ListField` の件数エラーの日本語訳がない | Frontend が 100 件までしか送らないので、通常は表示されない |
