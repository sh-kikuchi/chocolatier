# DB設計（Django側）

- 最終更新：2026-11-19（改修案件08 の「データの決まり」を追加。列の定義は 2026-11-18 に実際の DB と照合済み）
- DB は SQLite。表名は Django が自動で付ける `アプリ名_モデル名`（例：`chocolatier_api_snap`）
- `id` は Django の `BigAutoField`。SQLite では `integer`（自動採番）になる
- 列の記号：PK＝主キー / NN＝NOT NULL / FK＝外部キー / UQ＝一意

## ER 図（関係）

```
users ──1:N── snaps ──N:1── files
                │
                N
                │
            snap_tags（中間テーブル）
                │
                N
                │
              tags
```

- 1 人のユーザーが複数の Snap を持つ（Snap → User は多対1）
- 1 つの Snap は 1 つのファイルを持つ（Snap → File は多対1）
- Snap と Tag は多対多。`snap_tags` が「どの Snap にどのタグが付いているか」を持つ

## users テーブル（`chocolatier_api_user`）

- Django 標準の `AbstractUser` を継承したカスタムユーザー。`first_name` / `last_name` は削除している

| カラム名 | データ型 | PK | NN | FK | UQ | 備考 |
|---|---|---|---|---|---|---|
| id | BIGINT | ○ | ○ |  |  | ユーザーID（自動採番） |
| username | TEXT |  | ○ |  | ○ | ログインID。標準の `CharField` から `TextField` に変更している |
| email | VARCHAR(254) |  | ○ |  |  | メールアドレス（一意制約はない） |
| password | VARCHAR(128) |  | ○ |  |  | ハッシュ化したパスワード |
| is\_staff | BOOL |  | ○ |  |  | 管理画面に入れるか。サインアップ API を使えるのは `True` のユーザーだけ |
| is\_superuser | BOOL |  | ○ |  |  | すべての権限を持つか（`createsuperuser` で作ると `True`） |
| is\_active | BOOL |  | ○ |  |  | 有効なアカウントか |
| last\_login | DATETIME |  |  |  |  | 最終ログイン日時（管理画面のログインで更新される） |
| date\_joined | DATETIME |  | ○ |  |  | 登録日時 |

- 権限用の中間テーブル `chocolatier_api_user_groups` / `chocolatier_api_user_user_permissions` も Django が自動で作る（アプリでは使っていない）

## snaps テーブル（`chocolatier_api_snap`）

| カラム名 | データ型 | PK | NN | FK | UQ | 備考 |
|---|---|---|---|---|---|---|
| id | BIGINT | ○ | ○ |  |  | スナップID |
| user\_id | BIGINT |  | ○ | ○ |  | 投稿したユーザー（`users.id`）。ユーザーを削除すると Snap も削除 |
| file\_id | BIGINT |  | ○ | ○ |  | 画像ファイル（`files.id`）。ファイルを削除すると Snap も削除 |
| comment | TEXT |  |  |  |  | コメント（任意）。1000 文字までの制限はシリアライザーで行う |
| created\_at | DATETIME |  | ○ |  |  | 作成日時（自動）。一覧の並び順と、無限スクロールの cursor に使う |
| updated\_at | DATETIME |  | ○ |  |  | 更新日時（自動） |

- タグは、この表には列を持たない（`snap_tags` に入る）

## files テーブル（`chocolatier_api_file`）

| カラム名 | データ型 | PK | NN | FK | UQ | 備考 |
|---|---|---|---|---|---|---|
| id | BIGINT | ○ | ○ |  |  | ファイルID |
| name | VARCHAR(255) |  |  |  |  | ファイル名（任意） |
| path | VARCHAR(500) |  | ○ |  | ○ | `media/` からの相対パス（例：`uploads/photo_20260930120000.png`） |
| created\_at | DATETIME |  | ○ |  |  | 登録日時（自動） |
| updated\_at | DATETIME |  | ○ |  |  | 更新日時（自動） |

- `path` はファイル名に秒単位の日時を付けて作る。同じ名前の画像を同じ秒に 2 回アップロードすると、一意制約で 500 になる（既知の不具合。対象外として残している）

## tags テーブル（`chocolatier_api_tag`）※改修案件3で追加

- 全ユーザーで共通の表。同じ名前のタグは 1 行だけ作られる（alice の「旅行」と bob の「旅行」は同じ行）
- 絞り込みの候補（`GET /chocolatier_api/tags/`）には、自分の Snap に付いているタグだけを返すので、他のユーザーのタグは見えない

| カラム名 | データ型 | PK | NN | FK | UQ | 備考 |
|---|---|---|---|---|---|---|
| id | BIGINT | ○ | ○ |  |  | タグID |
| name | VARCHAR(30) |  | ○ |  | ○ | タグ名（30 文字まで） |
| created\_at | DATETIME |  | ○ |  |  | 作成日時（自動） |

## snap\_tags テーブル（`chocolatier_api_snap_tags`）※改修案件3で追加

- `Snap.tags = ManyToManyField('Tag')` から、Django が自動で作る中間テーブル
- 1 行が「この Snap にこのタグが付いている」を表す

| カラム名 | データ型 | PK | NN | FK | UQ | 備考 |
|---|---|---|---|---|---|---|
| id | BIGINT | ○ | ○ |  |  | 自動採番 |
| snap\_id | BIGINT |  | ○ | ○ | ※ | `snaps.id` |
| tag\_id | BIGINT |  | ○ | ○ | ※ | `tags.id` |

- ※ `(snap_id, tag_id)` の組み合わせで一意（同じ Snap に同じタグを 2 回付けられない）
- Snap またはタグを削除すると、その行も自動で削除される

## アプリ側の上限値（DB の制約ではないもの）

| 項目 | 上限 | チェックする場所 |
|---|---|---|
| 画像 | jpg / jpeg / png / gif / webp、5MB 以下 | `serializers/snap.py`・`validators.ts` |
| コメント | 1000 文字 | `serializers/snap.py`・`validators.ts` |
| 1 つの Snap のタグ | 10 個 | `serializers/snap.py`・`validators.ts` |
| タグ 1 つの文字数 | 30 文字（DB の列の長さと同じ） | `serializers/snap.py`・`validators.ts`・DB |

## データの決まり（改修案件08 で追加・2026-11-19）

| 項目 | 決まり | 守っている場所 |
|---|---|---|
| スナップと画像 | 1 対 1（業務の原則）。DB は多対 1（FK）のままで、削除の後片付けでこの原則を守る | `signals.py` |
| スナップの削除 | 画像（TBL-02 の行と実ファイル）も消す。API・管理画面・利用者の削除（CASCADE）のどれから消しても同じ | `signals.py` の `snap_deleted`・`file_deleted` |
| 使われていないタグ | どのスナップにも付いていないタグは消す（タグを付け替えたとき・スナップを消したとき）。残っていたものはマイグレーション 0003 で片付けた | `services/tags.py`、`migrations/0003_delete_unused_tags.py` |
| 利用者のメールアドレス | 大文字・小文字を区別せず重複禁止。空は重複を見ない。DB の一意制約ではない（空の利用者が複数いてもよいため） | `serializers/user.py` の `validate_email`（登録 API のみ） |
| スナップの作成 | 画像の保存・スナップの作成・タグ付けは 1 つのトランザクション。失敗したら実ファイルも消す | `serializers/snap.py` の `SnapCreateSerializer.create` |
