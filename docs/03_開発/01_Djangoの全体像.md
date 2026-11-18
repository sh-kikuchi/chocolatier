# Django（DRF）の全体像：ファイルの役割と開発の順番

- 最終更新：2026-11-19（改修案件08 の `views/media.py`・`signals.py`・`services/tags.py` を追加）

- Chocolatier の Backend を例に、「どのファイルが何の役割か」「リクエストがどう流れるか」「どの順番で作るか」をまとめる。
- 新しい機能を作るときの地図として使う。

> **改修案件7（2026-11-18）で更新**：`views.py`・`serializers.py`・`tests.py` を、それぞれ同じ名前の **フォルダ（パッケージ）** に分けた。あわせて、ファイルの保存・削除と Zip の作成を **`services/`（作業係）** に切り出した。1〜3 章はこの形に合わせて書き直している。5 章の改修案件3・4 の例は、当時のファイル名（`views.py` など）のまま残している。記録：[04\_改修事案/07\_Backendの整理.md](../04_改修事案/07_Backendの整理.md)

- [Django（DRF）の全体像：ファイルの役割と開発の順番](#djangodrfの全体像ファイルの役割と開発の順番)
  - [1. 全体の地図](#1-全体の地図)
  - [2. フォルダ構成と役割](#2-フォルダ構成と役割)
    - [■ プロジェクト（chocolatier_core）とアプリ（chocolatier_api）](#-プロジェクトchocolatier_coreとアプリchocolatier_api)
    - [■ ファイルごとの役割](#-ファイルごとの役割)
  - [3. 各層の役割](#3-各層の役割)
    - [■ manage.py：操作の入口](#-managepy操作の入口)
    - [■ settings.py：全体の設定](#-settingspy全体の設定)
    - [■ ミドルウェア：全リクエストが通る関所](#-ミドルウェア全リクエストが通る関所)
    - [■ urls.py：振り分け表](#-urlspy振り分け表)
    - [■ views/：窓口](#-views窓口)
    - [■ services/：作業係（改修案件7 で追加）](#-services作業係改修案件7-で追加)
    - [■ signals.py：消えたときの後片付け（改修案件08 で追加）](#-signalspy消えたときの後片付け改修案件08-で追加)
    - [■ authentication.py：誰かを判定する](#-authenticationpy誰かを判定する)
    - [■ serializers/：翻訳係](#-serializers翻訳係)
    - [■ models.py：データの設計図](#-modelspyデータの設計図)
    - [■ マイグレーション：設計図を DB に反映する](#-マイグレーション設計図を-db-に反映する)
    - [■ admin.py：管理画面](#-adminpy管理画面)
  - [4. リクエストの流れ（実例）](#4-リクエストの流れ実例)
    - [■ 例1：一覧を取得する（GET）](#-例1一覧を取得するget)
    - [■ 例2：画像を投稿する（POST）](#-例2画像を投稿するpost)
  - [5. 開発の順番](#5-開発の順番)
    - [■ 基本の順番：データに近い層から](#-基本の順番データに近い層から)
    - [■ 例：改修案件3（タグ）の順番](#-例改修案件3タグの順番)
    - [■ 例：改修案件4（無限スクロール）の順番](#-例改修案件4無限スクロールの順番)
  - [6. よく使うコマンド](#6-よく使うコマンド)

## 1\. 全体の地図

- リクエストは、**上から下へ**流れて処理される。レスポンスは、逆の順番で戻っていく。

```
ブラウザ / Postman
   │  GET /chocolatier_api/snap/?tag=旅行
   ▼
┌─────────────────────────────────────────────┐
│ settings.py   … アプリ全体の設定（全部の層が参照する）     │
└─────────────────────────────────────────────┘
   ▼
① ミドルウェア      … 全リクエストが通る関所（CORS・CSRF など）
   ▼
② urls.py         … 「この URL はどの View へ？」の振り分け表
   ▼
③ views/          … 窓口。認証・権限を確認し、処理の流れを決める
   │                 （例：自分の Snap を、?tag で絞って取ってくる）
   ├──▶ authentication.py … 「誰か？」を判定する
   ├──▶ services/  … 作業係。ファイルの保存・削除、Zip の作成など（HTTP のことは知らない）
   ▼
④ serializers/    … 翻訳係。JSON ⇔ Python のデータの変換と入力チェック
   ▼
⑤ models.py       … データの設計図。どんな表・列・関係があるか
   ▼
⑥ マイグレーション    … 設計図（models.py）を実際の DB に反映する手順書
   ▼
   DB（db.sqlite3）

⑦ admin.py        … 管理画面（/admin/）の設定（この流れとは別の入口）
```

## 2\. フォルダ構成と役割

### ■ プロジェクト（chocolatier\_core）とアプリ（chocolatier\_api）

- Django では、**プロジェクト**の中に、機能のまとまりである**アプリ**を入れる。
    - **プロジェクト**：サイト全体の設定と、URL の入口を持つ。1つだけ。
    - **アプリ**：機能ごとのまとまり（モデル・View・シリアライザーなど）。複数持てる。
- Chocolatier は、プロジェクトが `chocolatier_core`、アプリが `chocolatier_api` の1つだけ、という構成。

```
backend/
├── manage.py                 … 操作の入口（runserver / migrate など）
├── db.sqlite3                … DB 本体（SQLite）
├── media/uploads/            … アップロードされた画像
├── requirements.txt          … 必要なパッケージの一覧
│
├── chocolatier_core/         … 【プロジェクト】サイト全体
│   ├── settings.py           … 全体の設定
│   ├── urls.py               … URL の入口（ここからアプリの urls.py へ振り分ける）
│   ├── wsgi.py / asgi.py     … 本番サーバーとつなぐ入口（普段は触らない）
│   └── __init__.py
│
└── chocolatier_api/          … 【アプリ】Snap・ユーザー・タグの機能
    ├── models.py             … データの設計図
    ├── migrations/           … DB への反映手順（makemigrations で自動生成）
    │   ├── 0001_initial.py
    │   └── 0002_tag_snap_tags.py
    ├── serializers/          … 翻訳係：JSON ⇔ Python の変換と入力チェック
    │   ├── __init__.py       … 表札（下のファイルから import し直す）
    │   ├── snap.py           … Snap（一覧・作成・更新・削除・Zip）とタグの共通処理
    │   └── user.py           … ユーザー
    ├── views/                … 窓口：API の入口
    │   ├── __init__.py       … 表札（urls.py の `from .views import ...` がそのまま使える）
    │   ├── snap.py           … Snap の一覧・詳細・作成・Zip ダウンロード
    │   ├── tag.py            … タグ（絞り込みの候補）
    │   ├── user.py           … ユーザーの登録・ログイン中の情報
    │   ├── auth.py           … ログイン・refresh・ログアウト・CSRF
    │   └── media.py          … 画像の配信（ログインした持ち主だけ。改修案件08）
    ├── services/             … 作業係：HTTP を知らない「作業」
    │   ├── files.py          … 画像ファイルの保存・削除
    │   ├── zip.py            … Zip の作成・フォルダ名の安全化
    │   └── tags.py           … 使われていないタグの片付け（改修案件08）
    ├── signals.py            … 削除されたときの後片付け（実ファイル・タグ。改修案件08）
    ├── urls.py               … アプリ内の URL
    ├── pagination.py         … 一覧を何件ずつ返すか（自作。改修案件4）
    ├── authentication.py     … Cookie の JWT で「誰か」を判定する（自作）
    ├── admin.py              … 管理画面の設定
    ├── apps.py               … アプリの設定（普段は触らない）
    └── tests/                … 自動テスト
        ├── base.py           … 共通の部品（テスト用の設定・画像の作り方・ログイン済みの準備）
        ├── test_auth.py      … Cookie 認証・権限・サインアップ
        ├── test_snap.py      … 入力チェック・タグ・ページング
        ├── test_zip.py       … Zip ダウンロード
        ├── test_services.py  … services/ を API を通さずに直接テスト
        └── test_fixes.py     … 改修案件08 の対応（PUT・画像の公開範囲・後片付けなど）
```

- **フォルダ（パッケージ）に分ける方法**：`views.py` を `views/` に変えても、`views/__init__.py` で中身を import し直しておけば、外からは `from .views import SnapList` のまま使える。外から見た形を変えずに、中身だけを整理できる。
- **import の `.` の数**：`.` 1 つは「同じフォルダ」、2 つは「1 つ上のフォルダ」。`views/snap.py` から `models.py` を読むときは `from ..models import Snap` になる。
- **テストのファイル名**：Django は `test` で始まるファイルだけをテストとして探す（`base.py` はテストとして実行されない）。

### ■ ファイルごとの役割

| ファイル | ひとことで | 変えるのはどんなとき |
|---|---|---|
| `manage.py` | 操作の入口 | ほぼ変えない |
| `settings.py` | 全体の設定 | ライブラリの追加、認証方式の変更、上限値の追加 |
| `chocolatier_core/urls.py` | URL の入口 | アプリ全体に関わる URL（ログインなど）を追加するとき |
| `chocolatier_api/urls.py` | アプリ内の URL | API を追加するとき |
| `views/` | 窓口 | API の処理の流れ・権限を変えるとき |
| `services/` | 作業係 | ファイル・Zip など、HTTP と関係のない作業を変えるとき |
| `pagination.py` | 区切り方 | 一覧の件数や並び順、ページングの方式を変えるとき |
| `authentication.py` | 誰かを判定 | 認証方式を変えるとき |
| `serializers/` | 翻訳係 | レスポンスの形、受け取る項目、入力チェックを変えるとき |
| `tests/` | 自動テスト | 機能を足した・変えたとき（`test_` で始まるファイルに書く） |
| `models.py` | 設計図 | 表・列・関係を追加・変更するとき（→ マイグレーションが必要） |
| `migrations/` | DB への反映手順 | 自分では書かない（`makemigrations` で作る） |
| `admin.py` | 管理画面 | 管理画面に表示するモデルや項目を変えるとき |

## 3\. 各層の役割

### ■ manage.py：操作の入口

- `runserver`・`makemigrations`・`migrate`・`createsuperuser` などは、すべて `manage.py` 経由で動く。
- 最初に「どの settings.py を使うか」（`chocolatier_core.settings`）を Django に教える。
    - そのため、**`backend` フォルダで、venv を有効にしてから**実行する。
    - 別の場所から実行すると `No module named 'chocolatier_core'` になる。

### ■ settings.py：全体の設定

- すべての層が参照する設定。
- Chocolatier で主に使っている設定
    - `INSTALLED_APPS`：使うアプリ・ライブラリ（`rest_framework`・`corsheaders`・`chocolatier_api` など）
    - `MIDDLEWARE`：ミドルウェアの順番
    - `REST_FRAMEWORK`：DRF 全体の認証・権限のデフォルト
    - `AUTH_USER_MODEL`：カスタムユーザーモデル（`chocolatier_api.User`）
    - `MAX_UPLOAD_SIZE` など：自作の定数（上限値）

### ■ ミドルウェア：全リクエストが通る関所

- `settings.py` の `MIDDLEWARE` に、**上から順に**並べる。リクエストは上から、レスポンスは下から通る。
- 例
    - `CorsMiddleware`：別オリジン（localhost:3000）からのアクセスを許可するヘッダーを付ける
    - `CsrfViewMiddleware`：CSRF 対策
- 並び順に意味がある。`CorsMiddleware` は `CommonMiddleware` より前に置く（→ [03\_認証.md](03_認証.md)）。

### ■ urls.py：振り分け表

- URL と View を結びつける。上から順に照合し、最初に一致した View に処理を渡す。
- プロジェクトの `urls.py` から、`include` でアプリの `urls.py` を取り込む。

```python
# chocolatier_core/urls.py（プロジェクト）
path('chocolatier_api/', include('chocolatier_api.urls')),

# chocolatier_api/urls.py（アプリ）
path('snap/', SnapList.as_view()),   # → 実際の URL は /chocolatier_api/snap/
path('snap/<int:pk>/', SnapDetail.as_view()),  # <int:pk> の数字が View に渡る
```

### ■ views/：窓口

- リクエストを受け取り、**処理の流れ**を決める。
    - 誰が使ってよいか（`permission_classes`）
    - どのデータを扱うか（`get_queryset`）
    - どのシリアライザーを使うか（`serializer_class`）
- DRF の `generics` を継承すると、よくある処理（一覧・作成・詳細・更新・削除）をほとんど書かずに作れる。

| View の親クラス | できること | Chocolatier での例 |
|---|---|---|
| `APIView` | 自分で `get` / `post` を書く | `UserSignup`・`CookieLoginView` |
| `ListAPIView` | 一覧（GET） | `SnapList` |
| `CreateAPIView` | 作成（POST） | `SnapCreate` |
| `RetrieveUpdateDestroyAPIView` | 詳細・更新・削除 | `SnapDetail` |

- View に書くのは「流れ」だけにして、データの変換や入力チェックはシリアライザーに、実際の作業は services/ に任せる。

### ■ services/：作業係（改修案件7 で追加）

- ファイルの保存・削除や Zip の作成など、**実際の作業** を関数として置く。
- **HTTP のこと（`request`・`Response`・ステータスコード）は知らない作りにする**。結果を返すだけで、それを見て 404 などを返すかどうかは View が決める。

| 関数 | 受け取るもの | 返すもの | 呼ぶ場所 |
|---|---|---|---|
| `services/files.py` の `save_upload` | アップロードされた画像 | 作った `File` | `SnapCreateSerializer.create` |
| `services/files.py` の `delete_file` | `File`（`None` なら何もしない） | なし | `SnapDeleteSerializer.delete` |
| `services/zip.py` の `safe_folder_name` | タグ名（`None` 可） | Zip の中のフォルダ名 | `SnapZipDownload.post` |
| `services/zip.py` の `build_snap_zip` | Snap の一覧・フォルダ名 | `(一時ファイル, 入れた枚数)` | `SnapZipDownload.post` |
| `services/files.py` の `remove_physical_file` | `File.path` | なし（実ファイルだけを消す） | `signals.py`・作成に失敗したとき |
| `services/tags.py` の `delete_unused_tags` | なし | 消したタグの数 | `set_snap_tags`・`signals.py` |

- 良いところ
    - View が短くなり、「流れ」が読みやすくなる（`SnapZipDownload.post` は Zip の作り方を知らなくてよい）
    - 作業だけを API を通さずにテストできる（`tests/test_services.py`）
    - 別の場所（管理画面・コマンドなど）からも同じ作業を呼べる
- Frontend で、切り抜きの処理を `utils/cropImage.ts` に分けて部品（`ImageCropper`）から切り離したのと同じ考え方。

### ■ signals.py：消えたときの後片付け（改修案件08 で追加）
- **シグナル**：モデルの保存・削除などのタイミングで、Django が自動で呼んでくれる関数。
- Chocolatier では、スナップや画像（File）が消えたあとの後片付けに使う。

| シグナル | すること |
|---|---|
| Snap の `post_delete` | その画像（File の行）を消し、どのスナップにも付いていないタグを消す |
| File の `post_delete` | 実ファイル（`media/uploads/...`）を消す |

- API から消しても、管理画面から消しても、利用者ごと消しても（CASCADE）、同じ後片付けが動く。
- `apps.py` の `ready()` で `from . import signals` しないと登録されない（ファイルを置いただけでは動かない）。

### ■ authentication.py：誰かを判定する

- `settings.py` の `DEFAULT_AUTHENTICATION_CLASSES` に登録すると、View の処理の前に自動で呼ばれる。
- ここで判定したユーザーが `request.user` になる。
- Chocolatier では、Cookie の JWT を読む `CookieJWTAuthentication` を自作している（→ [03\_認証.md](03_認証.md)）。
- **認証**（誰か？）と**権限**（使ってよいか？）は別もの。
    - 認証：`authentication_classes`。分からなければ 401
    - 権限：`permission_classes`。許可していなければ 403

### ■ serializers/：翻訳係

- 2つの方向の変換をする。
    - **受け取るとき**：JSON（文字列）→ Python のデータ。あわせて入力チェックも行う（→ [06\_入力チェック.md](06_入力チェック.md)）
    - **返すとき**：モデル（Python のオブジェクト）→ JSON
- `ModelSerializer` を使うと、モデルの定義から項目を自動で作ってくれる。
- 「レスポンスにどの項目を出すか」「どの項目を受け取るか」は、ここの `fields` で決める。

### ■ models.py：データの設計図

- 1つのクラスが DB の1つの表、1つの属性が1つの列になる。
- モデルどうしの関係も、ここで定義する。

| 関係 | 書き方 | Chocolatier での例 |
|---|---|---|
| 多対1 | `ForeignKey` | Snap → User（1人のユーザーが複数の Snap を持つ） |
| 多対多 | `ManyToManyField` | Snap ⇔ Tag（中間テーブル `snap_tags` が自動で作られる） |
| 1対1 | `OneToOneField` | （今は未使用） |

- models.py を変えただけでは、DB は変わらない。次のマイグレーションが必要。

### ■ マイグレーション：設計図を DB に反映する

- 2つのステップで行う。

| コマンド | すること | DB は変わる？ |
|---|---|---|
| `makemigrations` | models.py の変更点を「手順書」（`0002_...py`）にする | 変わらない |
| `migrate` | まだ適用していない手順書を、順番に DB に反映する | 変わる |

- 手順書は `dependencies` で順番がつながっている（0002 は 0001 の後）。
- 手順書は git にコミットする。他の環境でも `migrate` するだけで、同じ DB の構造にできる。
- 自分で書くことはほぼない。`makemigrations` が作ったものを確認するだけ。

### ■ admin.py：管理画面

- `/admin/` の管理画面に、どのモデルをどう表示するかを設定する。
- API とは別の入口。API を作る前に、データを入れて動作を確かめる道具としても使える。
- ログインには、`createsuperuser` で作った管理者を使う（Django のセッション認証。API の Cookie JWT とは別）。

## 4\. リクエストの流れ（実例）

### ■ 例1：一覧を取得する（GET）

`GET /chocolatier_api/snap/`

| 順番 | 層 | 起きること |
|---|---|---|
| 1 | ミドルウェア | CORS の確認。Cookie を読み込む |
| 2 | `chocolatier_core/urls.py` | `chocolatier_api/` に一致 → アプリの urls.py へ |
| 3 | `chocolatier_api/urls.py` | `snap/` に一致 → `SnapList` へ |
| 4 | `authentication.py` | `access_token` Cookie を検証 → `request.user` = alice |
| 5 | `views/snap.py`（権限） | `IsAuthenticated` → ログイン中なので OK |
| 6 | `views/snap.py`（`get_queryset`） | `Snap.objects.filter(user=alice)`。`?tag=` があればタグで絞る |
| 7 | `pagination.py` | 新しい順に並べて、12 件だけに区切る（続きの URL `next` も作る） |
| 8 | `models.py` → DB | SQL が発行されて、alice の Snap を取得する（file・tags はまとめて取る） |
| 9 | `serializers/snap.py` | Snap のオブジェクト → JSON（`id`・`filePath`・`comment`・`tags` など）。`{next, previous, results}` に包む |
| 10 | ミドルウェア → ブラウザ | CORS ヘッダーを付けて、200 で返す |

### ■ 例2：画像を投稿する（POST）

`POST /chocolatier_api/snap/create/`（multipart：upload, comment）

| 順番 | 層 | 起きること |
|---|---|---|
| 1〜3 | ミドルウェア・urls.py | `SnapCreate` へ |
| 4 | `authentication.py` | Cookie を検証し、**CSRF もチェック**（POST なので） |
| 5 | `views/snap.py` | `SnapCreateSerializer` にデータを渡す |
| 6 | `serializers/snap.py`（チェック） | 画像か？拡張子は？5MB 以下？コメントは 1000 文字以内？ → NG なら 400 |
| 7 | `views/snap.py`（`perform_create`） | `serializer.save(user=request.user)`：投稿者をログインユーザーにする |
| 8 | `serializers/snap.py`（`create`）→ `services/files.py` | トランザクションの中で、画像を `media/uploads/` に保存して、File と Snap を作り、タグを付ける（失敗したら全部取り消し、画像も消す） |
| 9 | `models.py` → DB | INSERT の SQL が発行される |
| 10 | `serializers/snap.py` → ブラウザ | 作成した Snap を JSON にして、201 で返す |

## 5\. 開発の順番

### ■ 基本の順番：データに近い層から

- 新しい機能は、**データに近い層（下）から、利用者に近い層（上）へ**作る。
- 下の層は、上の層から「部品」として使われる。部品がないと、上の層は書けないし試せない。

```
① models.py        設計図を決める（すべての土台）
   ↓
② マイグレーション     DB に反映する
   ↓
③ admin.py         管理画面でデータを入れて、設計図が正しいか確かめる
   ↓
④ serializers/     JSON でどう見せるか・どう受け取るかを決める（作業は services/ に任せる）
   ↓
⑤ views/           serializer・service を使って、処理の流れと権限を組み立てる
   ↓
⑥ urls.py          URL を登録して、外から呼べるようにする
   ↓
⑦ curl / Postman   API の動作を確かめる
   ↓
⑧ フロントエンド      API を使う画面を作る
```

- 各段階で動作を確かめてから次へ進むと、問題が起きたときに原因の層をすぐ絞り込める。

### ■ 例：改修案件3（タグ）の順番

| 順番 | Step | 層 | 理由 |
|---|---|---|---|
| 1 | B1 | `models.py` | タグの表と、Snap との多対多の関係を決める |
| 2 | B2 | マイグレーション | `snap_tags` の中間テーブルと `tag` の表を DB に作る |
| 3 | B5 | `admin.py` | 管理画面で Snap にタグを付けてみて、関係が正しいか確かめる |
| 4 | B3 | `serializers.py` | レスポンスに `tags: ["旅行"]` を出す。作成・更新でタグを受け取る |
| 5 | B4 | `views.py` → `urls.py` | `?tag=` での絞り込みと、`tags/` の API を追加する |
| 6 | F1〜 | フロントエンド | タグ入力と、絞り込みのチップを作る |

- 詳しくは [07\_タグ.md](07_タグ.md)。

### ■ 例：改修案件4（無限スクロール）の順番

- 表や列は変わらないので、models・マイグレーション・admin は飛ばして、View のまわりから作る。

| 順番 | Step | 層 | 理由 |
|---|---|---|---|
| 1 | B1 | `pagination.py`（新規） | 「12 件ずつ・新しい順」のルールを決める |
| 2 | B2 | `views.py` | `SnapList` に B1 のルールを付ける。レスポンスの形が変わる |
| 3 | — | curl / API 画面 | `next` をたどって、重複や抜けがないか確かめる |
| 4 | F1〜 | フロントエンド | `next` を使って続きを読み込む（返ってくる形が決まってから作る） |

- 詳しくは [08\_無限スクロール.md](08_無限スクロール.md)。

## 6\. よく使うコマンド

- すべて `backend` フォルダで、venv を有効にしてから実行する。

```powershell
cd backend
venv\Scripts\activate
```

| コマンド | すること |
|---|---|
| `python manage.py runserver` | 開発サーバーを起動（[http://localhost:8000）](http://localhost:8000）) |
| `python manage.py check` | 設定やコードに問題がないか確認 |
| `python manage.py makemigrations chocolatier_api` | models.py の変更から、マイグレーションファイルを作る |
| `python manage.py sqlmigrate chocolatier_api 0002` | マイグレーションで実行される SQL を見る |
| `python manage.py showmigrations` | どのマイグレーションが適用済みか見る（`[X]` が適用済み） |
| `python manage.py migrate` | マイグレーションを DB に反映 |
| `python manage.py createsuperuser` | 管理者ユーザーを作る |
| `python manage.py shell` | Django の設定を読み込んだ Python を起動（モデルを直接操作して試せる） |
| `python manage.py test` | 自動テストを実行 |
