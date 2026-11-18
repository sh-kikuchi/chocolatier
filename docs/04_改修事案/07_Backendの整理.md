# 改修案件7：Backend の整理（ファイルの切り出し）

- 対象：Chocolatier（backend: Django + DRF）
- 作成日：2026-11-17
- 状態：完了（2026-11-18。M1〜M6 すべて完了。Backend のテスト 52 件が通過）
- 関連：[03\_開発/01\_Djangoの全体像.md](../03_開発/01_Djangoの全体像.md)（Django の全体像）

> **最新の状態（2026-11-19 追記）**
>
> - 改修案件08 で、`views/media.py`・`signals.py`・`services/tags.py`・`tests/test_fixes.py` が増えた。今の構成は [03_開発/01_Djangoの全体像.md](../03_開発/01_Djangoの全体像.md)

## 1\. 背景

| # | 課題 | 該当箇所 |
|---|---|---|
| 1 | 1 つのファイルに、役割の違うものが全部入っていて読みにくい（Snap・タグ・Zip・ユーザー・ログイン／Cookie） | `views.py`（409 行） |
| 2 | ファイルの保存・削除という「作業」が、翻訳係（Serializer）の中にある | `serializers.py`（345 行）の `FileUploadSerializer` / `FileDeleteSerializer` |
| 3 | Zip を作る「作業」が、窓口（View）の中にある。Zip の処理だけをテストできない | `views.py` の `SnapZipDownload` |
| 4 | デバッグ用の `print` が残っていて、削除のたびにログに出る | `serializers.py`（12 か所） |
| 5 | すべての機能のテストが 1 ファイルにある | `tests.py`（535 行） |

## 2\. 決定事項

| 項目 | 方針 |
|---|---|
| ゴール | **動きは一切変えずに、ファイルを役割ごとに分ける**。API・DB・Frontend は変更なし |
| 分け方 | `views.py` / `serializers.py` / `tests.py` を、同じ名前の **フォルダ（パッケージ）** にして中で分ける |
| import の互換 | `views/__init__.py` と `serializers/__init__.py` で中身を import し直す → `from .views import SnapList` のような今の書き方がそのまま動く（`urls.py` は変えなくてよい） |
| 作業の切り出し | ファイルの保存・削除、Zip の作成を `services/` に移す。View と Serializer は `services` を呼ぶだけにする |
| 壊していないことの確認 | 各マイルストーンの最後に、既存のテスト（47 件）がすべて通ることを確かめる |
| 対象外（今後の課題） | 認証を別アプリ（`accounts`）にする／`settings.py` の秘密の値を `.env` に出す／ファイルの保存を `ImageField` にする（→ 7 章） |

### 整理後の形

```
chocolatier_api/
  views/
    __init__.py      … 下のファイルから import して並べるだけ
    snap.py          … SnapList / SnapDetail / SnapCreate / SnapZipDownload
    tag.py           … TagList
    user.py          … UserSignup / UserInfoView
    auth.py          … set_auth_cookies / CookieLoginView / CookieRefreshView / LogoutView / CsrfView
  serializers/
    __init__.py
    snap.py          … SnapSerializer / SnapCreate・Update・Delete・ZipDownloadSerializer、clean_tag_names / set_snap_tags
    user.py          … UserSerializer
  services/
    __init__.py
    files.py         … save_upload(upload) / delete_file(file_obj)（今の FileUpload・FileDeleteSerializer の中身）
    zip.py           … build_snap_zip(snaps, folder_name) / safe_folder_name(tag)
  tests/
    __init__.py
    base.py          … 共通の部品（TEST_SETTINGS / make_image / BaseAPITestCase）
    test_auth.py     … Cookie 認証・権限・サインアップ
    test_snap.py     … 入力チェック・タグ・ページング
    test_zip.py      … Zip ダウンロード
    test_services.py … services/ の単体テスト（M5 で追加。計画では test_zip.py に入れる予定だった）
  models.py / urls.py / admin.py / authentication.py / pagination.py は変更なし
```

### 「services」に切り出す理由

| 係 | 仕事 | 今回の例 |
|---|---|---|
| View（窓口） | リクエストを受けて、各係に仕事を頼み、返事を返す | `SnapZipDownload`：チェック → 絞り込み → `build_snap_zip` を呼ぶ → 返す |
| Serializer（翻訳係） | JSON ⇔ Python の変換と、入力チェック | `SnapZipDownloadSerializer` |
| **Service（作業係）** | 実際の作業（ファイル・Zip など）。HTTP のことは知らない | `build_snap_zip`：Snap の一覧を受け取り、Zip を作るだけ |

Frontend で `cropImage.ts` を `ImageCropper` から切り離したのと同じ考え方。作業だけを単独でテストでき、別の画面（管理画面・コマンドなど）からも使える。

* * *

## 3\. 対応内容

| ファイル | 内容 |
|---|---|
| `serializers.py` | `print("DEBUG: ...")` を 12 か所削除 |
| `views.py` → `views/` | 4 つのファイルに分ける。`__init__.py` で import し直す |
| `serializers.py` → `serializers/` | 2 つのファイルに分ける。`FileUploadSerializer` / `FileDeleteSerializer` は `services/files.py` に移して削除 |
| `services/`（新規） | `files.py`・`zip.py` |
| `tests.py` → `tests/` | 4 つのファイルに分ける。`services/zip.py` の単体テストを追加 |
| `docs/03_開発/01_Djangoの全体像.md` | フォルダ構成・ファイルの役割の表に、`views/`・`serializers/`・`services/`・`tests/` を反映 |
| この文書 | 状態・計画からの変更点を更新 |

* * *

## 4\. 進める順番

| # | 作業 | 理由 |
|---|---|---|
| 1 | `print` の削除 | 一番小さく、次の作業で移すコードを先にきれいにしておける |
| 2 | `views/` に分ける | 一番大きいファイル。`__init__.py` で import し直す方法を、ここで覚える |
| 3 | `serializers/` に分ける | 2 と同じやり方の復習 |
| 4 | `tests/` に分ける | 5 で単体テストを足す場所を先に作っておく |
| 5 | `services/` に切り出す | 1〜4 で置き場所が整ってから、中身を動かす（一度に両方やると、壊したときに原因がわかりにくい） |
| 6 | Docs | 実際の形に合わせて書く |

* * *

## 5\. マイルストーン（2026-11-18〜11-23）

- 担当：実装はユーザー、テスト・レビュー・Docs はレビュアー
- 1 日あたり 1 時間前後の想定
- 行数は「移す行 / 新しく書く行」の目安（ほとんどがコピー＆貼り付け）
- **どのマイルストーンも、完了の目安は「既存のテスト 47 件がすべて通る」**

| # | 日付 | マイルストーン | 担当 | 作業 | 行数の目安 | 時間 | 完了の目安 |
|---|---|---|---|---|---|---|---|
| M1 | 11/17（火）**完了** | デバッグ出力を消す | レビュアー（担当を変更） | `serializers.py` の `print` を 12 か所削除。`print` のためだけにあった「実ファイルのパスを確認する」処理と、関数の中の重複した import も削除 | 0 / 0（12 行削除） | 15 分 | テストが通る。削除してもログに `DEBUG:` が出ない |
| M2 | 11/17（火）**完了** | **views を分ける** | レビュアー（担当を変更） | `views/` を作って 4 ファイルに分け、`__init__.py` で import し直す。古い `views.py` を消す | 400 / 30 | 1 時間 | テストが通る。`urls.py` は変えていない |
| M3 | 11/17（火）**完了** | serializers を分ける | レビュアー（担当を変更） | `serializers/` を作って **3** ファイル（snap / user / **file**）に分ける。`file.py` は M5 で `services/files.py` に移すまでの仮置き。あわせて、古いファイル名（`views.py` / `serializers.py`）を指していた `settings.py`・`models.py`・`pagination.py` のコメントを直した | 330 / 20 | 45 分 | テストが通る |
| M4 | 11/17（火）**完了**（関数の中の `from .pagination` を `..pagination` に直した） | tests を分ける | レビュアー | `tests/` を作って 4 ファイル（base / test\_auth / test\_snap / test\_zip）に分ける。行の範囲を指定するスクリプトで機械的に切り分けた | 535 / 20 | ユーザーの作業なし | テスト 47 件が、分けたあとも同じ数だけ実行されて通る |
| M5 | 11/18（水）**完了** | **services に切り出す（Backend 完成）** | レビュアー（担当を変更） | `services/files.py`・`zip.py` を作り、Serializer と View から呼ぶ形にする。レビュアーが `zip.py` の単体テストを追加 | 80 / 30（レビュアー 40） | 1.5〜2 時間 | テストが通る。`SnapZipDownload` の `post` が 20 行以内になる |
| M6 | 11/18（水）**完了** | **完了** | レビュアー → ユーザー | `01_Djangoの全体像.md` とこの文書を更新。ユーザーが内容を確認 | レビュアー：記事 40、この文書 20 | ユーザーの確認 15 分 | 状態を「完了」にする |
|  |  | **合計（ユーザー分）** |  |  | **ほぼコピー＆貼り付け。新しく書くのは約 80 行** | **3.5〜4 時間** |  |

### 山場と注意点

| M | 内容 |
|---|---|
| M2 | 分けたファイルどうしの import に注意。たとえば `views/snap.py` から `serializers` を読むときは `from ..serializers import ...`（`.` が 2 つ）になる。`.` 1 つは「同じフォルダ」、2 つは「1 つ上のフォルダ」 |
| M2・M3 | `views.py` と `views/` が **同時にあると、Python は `views/` の方を優先** する。分け終わったら古いファイルは必ず消す |
| M4 | テストのファイル名は `test_` で始める（Django はこの名前のファイルだけをテストとして探す） |
| M5 | `services` は HTTP（`Response` / `request`）を知らない作りにする。404 を返すかどうかは View が決める（`build_snap_zip` は「入れた枚数」を返すだけ） |

* * *

## 6\. 確認項目

| # | 内容 | 期待 |
|---|---|---|
| A1 | `python manage.py check` | エラーなし |
| A2 | `python manage.py test chocolatier_api` | 47 件（＋ M5 で追加した分）がすべて通る → **52 件すべて通過**（M5 で 5 件追加） |
| A3 | `urls.py`・`models.py`・Frontend の差分 | なし |
| B1 | ブラウザで、ログイン → 一覧 → 新規作成（トリミング）→ 更新 → 削除 → Zip ダウンロード | 今までどおり動く |

* * *

## 7\. 今後の課題（今回は対象外）

| 課題 | 内容 | 大きさ |
|---|---|---|
| 認証を別アプリにする | ログイン・Cookie・CSRF・ユーザー登録を `accounts` アプリに移す。`chocolatier_core/urls.py` が `chocolatier_api.views` を直接 import している状態も解消する。ただし `User` モデルの移動はマイグレーションが難しいので、モデルは残して View と URL だけ移す | 中 |
| 秘密の値を `.env` に出す | `SECRET_KEY` が直接書かれていて、`DEBUG = True` のまま。公開する前には必須 | 小 |
| ファイルの保存を `ImageField` にする | 今は保存・削除を自前で書いている。「同じ名前の画像を同じ秒に 2 回アップロードすると 500」という既知の不具合も、Django の `ImageField(upload_to=...)` なら自動で名前をずらしてくれる。DB の構造が変わるので、一番大きい | 大 |

* * *

## 8\. 計画からの変更点（実施後に追記）

| 項目 | 計画 | 実際 | 理由 |
|---|---|---|---|
| 担当 | M1〜M3・M5 はユーザー | すべてレビュアー | ユーザーの希望で変更 |
| `serializers/` の分け方 | 2 ファイル（snap / user） | M3 では 3 ファイル（＋ `file.py`）。`file.py` は M5 で `services/files.py` に移して削除し、最終的に 2 ファイル | M5 で移すものを、先に別ファイルにしておくとわかりやすいため |
| `print` の削除 | `print` の 12 行を消す | `print` のためだけにあった「実ファイルのパスを確認する」処理と、関数の中の重複した import も削除 | 動きに関係しないため |
| `services/files.py` | Serializer の中身を移す | Serializer の形をやめて、ただの関数（`save_upload` / `delete_file`）にした。`name` を外から受け取る分岐は、渡す呼び出し元がないので削除 | 入力チェックは `SnapCreateSerializer` が済ませているため |
| `seek(0)` の場所 | 記載なし | `build_snap_zip` の中に移した | 呼び出し元が忘れて空の Zip を返す心配をなくすため |
| 単体テストの置き場所 | `test_zip.py` に追加 | `tests/test_services.py`（新規、5 件）。`safe_folder_name`・`build_snap_zip`・`save_upload` / `delete_file` を API を通さずに確かめる | 作業係だけのテストとしてまとめた方が探しやすいため |
| 「`post` が 20 行以内」 | 20 行以内 | コメントを除いて 30 行（以前は Zip の作り方 約 20 行を含んでいた） | `Response(...)`・`FileResponse(...)` の呼び出しが複数行にまたがっているため。Zip の作り方は View から完全になくなった |
| 古いコメント | 記載なし | `settings.py`・`models.py`・`pagination.py` のコメントに残っていた古いファイル名（`views.py` など）を直した | ファイルを分けたため |
