# Git とリポジトリ

- 最終更新：2026-11-19

## 1. リポジトリ
| 項目 | 内容 |
|---|---|
| リモート（origin） | `https://github.com/sh-kikuchi/chocolatier.git`（`git remote -v` で確認。下の 3 章の控えは、最初に作ったときの別のアカウントの URL） |
| 主なブランチ | `main`（基本）・`develop`（開発のまとめ）・`feat_*`（作業用。例：`feat_kikuchi`） |
| git に入れないもの | `backend/db.sqlite3`・`backend/media/`・`venv`・`node_modules`・`frontend/build` など（`.gitignore`） |

## 2. コミットメッセージの形
英語で **`接頭辞:内容_yyyymmdd`**（内容は単語を `-` でつなぐ）。

| 接頭辞 | 使うとき | 例 |
|---|---|---|
| `feat` | 機能の追加・変更 | `feat:chocolatier-title-and-favicon_20261101` |
| `fix` | 不具合の修正 | `fix:delete-files-on-admin-delete_20261119` |
| `docs` | ドキュメントだけ | `docs:mark-renovation-complete_20261008` |
| `style` | 見た目・書き方だけ（動きは変えない） | `style:move-error-messages-to-top_20261008` |
| `test` | テストだけ | `test:add-zip-download-tests_20261113` |
| `refactor` | 動きを変えない整理 | `refactor:split-views-into-package_20261117` |
| `chore` | 設定・道具まわり | `chore:ignore-db-backup_20261003` |

## 3. GitHub でリポジトリを作ったときのコマンド（控え）
```
1. …or create a new repository on the command line

echo "# chocolatier" >> README.md
git init
git add README.md
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/t-moro437/chocolatier.git
git push -u origin main


2. …or push an existing repository from the command line

git remote add origin https://github.com/t-moro437/chocolatier.git
git branch -M main
git push -u origin main
```
