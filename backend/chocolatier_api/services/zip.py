# =========================================================
# services/zip.py
# - Zip の作成と、Zip の中のフォルダ名を安全にする処理（作業係）
# - 中身は views/snap.py の SnapZipDownload.post の ④ と ⑤ から移した
# - HTTP のことは知らない：404 を返すかどうかは、返した「入れた枚数」を見て View が決める
# =========================================================
import os                                # ファイルパスの組み立て
import re                                # 正規表現（フォルダ名に使えない記号の置き換え）
import tempfile                          # Zip を書き込む一時ファイル
import zipfile                           # Zip を作る標準ライブラリ

from django.conf import settings         # MEDIA_ROOT（画像の保存先）を読むため


# =========================================================
# safe_folder_name：タグ名から、Zip の中で使うフォルダ名を作る
# - 受け取るもの：tag（タグ名。「すべて」のときは None）
# - 返すもの    ：フォルダ名（文字列）
# - 例：'旅行' → '旅行'、'旅行/2026' → '旅行_2026'、'..' → 'すべて'、None → 'すべて'
# =========================================================
def safe_folder_name(tag):
    # ① フォルダ名に使えない記号（\ / : * ? " < > |）は「_」に置き換え、前後の空白と「.」を取る
    #    （「/」があると Zip の中でフォルダが分かれ、「..」があると解凍先の外に出てしまうため）
    safe_tag = re.sub(r'[\\/:*?"<>|]', '_', tag or '').strip(' .')

    # ② 何も残らなければ「すべて」
    return safe_tag or 'すべて'


# =========================================================
# build_snap_zip：Snap の画像を Zip にまとめた一時ファイルを作る
# - 受け取るもの：snaps（Snap の一覧。select_related('file') 済み）、folder_name（Zip の中のフォルダ名）
# - 返すもの    ：(zip_file, added) のタプル
#                 zip_file … Zip を書き込んだ一時ファイル（読む位置は先頭に戻してある）
#                 added    … Zip に入れた枚数（0 なら、呼び出し元が 404 にする）
# - 一時ファイルを閉じるのは呼び出し元（FileResponse が送り終わったら閉じる / 0 枚なら View が閉じる）
# =========================================================
def build_snap_zip(snaps, folder_name):
    # ① 一時ファイルを作る
    #    - TemporaryFile：閉じると自動で消える一時ファイル
    #    - with で開かない（返す前に閉じて消えてしまうため）
    zip_file = tempfile.TemporaryFile()
    added = 0

    # ② Zip に 1 枚ずつ書き込む
    #    - ZIP_STORED：圧縮しない（JPEG / PNG はもともと圧縮済みのため）
    with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_STORED) as zf:
        for snap in snaps:
            # ②-1 実ファイルのパスを作る（Windows の「\」を「/」にそろえる）
            full_path = os.path.join(settings.MEDIA_ROOT, snap.file.path.replace('\\', '/'))

            # ②-2 実ファイルがなければ飛ばす（1 枚欠けていても他は渡す）
            if not os.path.exists(full_path):
                continue

            # ②-3 Zip に追加する
            #      - arcname：Zip の中での名前（「旅行/photo_20261001120000.jpg」）
            #        指定しないと C:\Users\... のパスがそのままフォルダになる
            zf.write(full_path, arcname=f'{folder_name}/{os.path.basename(full_path)}')
            added += 1

    # ③ 読む位置を先頭に戻して返す
    #    - 書き込み後は読む位置がファイルの最後にあるので、戻さないと空の Zip が返る
    #    - ここで戻しておけば、呼び出し元は気にしなくてよい
    zip_file.seek(0)
    return zip_file, added
