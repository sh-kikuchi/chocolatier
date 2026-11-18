# =========================================================
# services/files.py
# - 画像ファイルの保存と削除（作業係）
# - 中身は serializers/file.py の FileUploadSerializer.create / FileDeleteSerializer.delete_file から移した
#   （Serializer の形をやめて、ただの関数にした。入力チェックは SnapCreateSerializer が済ませているため）
# =========================================================
import os                                # ファイルパスの組み立て
from datetime import datetime            # ファイル名に付ける日時

from django.conf import settings         # MEDIA_ROOT（画像の保存先）を読むため

from ..models import File


# =========================================================
# save_upload：アップロードされた画像を保存して、File（DB の行）を返す
# - 受け取るもの：upload（アップロードされたファイル。SnapCreateSerializer の validated_data['upload']）
# - 返すもの    ：File（作った DB の行）
# - 呼ぶ場所    ：serializers/snap.py の SnapCreateSerializer.create
# =========================================================
def save_upload(upload):
    # ① 新しいファイル名を作る（<元の名前>_<yyyymmddHHMMSS><拡張子>）
    original_name, ext = os.path.splitext(upload.name)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    new_filename = f"{original_name}_{timestamp}{ext}"

    # ② 保存先のパスを作る（MEDIA_ROOT/uploads/<新しいファイル名>）。フォルダがなければ作る
    #    - save_path：DB に入れる「MEDIA_ROOT から見た」パス（uploads/xxx.jpg）
    #    - full_path：実際に書き込む場所（C:\...\media\uploads\xxx.jpg）
    save_path = os.path.join("uploads", new_filename)
    full_path = os.path.join(settings.MEDIA_ROOT, save_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    # ③ 実際に保存する（大きいファイルでもメモリを使いすぎないよう、少しずつ書き込む）
    with open(full_path, "wb+") as f:
        for chunk in upload.chunks():
            f.write(chunk)

    # ④ DB に登録して、File を返す
    #    - 登録に失敗したら、③で書いた実ファイルを消してから失敗を伝える（実ファイルだけが残らないように）
    try:
        return File.objects.create(name=new_filename, path=save_path)
    except Exception:
        remove_physical_file(save_path)
        raise


# =========================================================
# full_path_of：DB の path（uploads/xxx.jpg）から、実ファイルの場所を作る
# - Windows で保存した path は「uploads\xxx.jpg」になっていることがあるので、「/」にそろえる
# =========================================================
def full_path_of(path):
    return os.path.join(settings.MEDIA_ROOT, path.replace("\\", "/"))


# =========================================================
# remove_physical_file：実ファイルだけを消す（DB は触らない）
# - 受け取るもの：path（File.path）
# - すでに無ければ何もしない
# - 呼ぶ場所：signals.py（File が消えたとき）、save_upload・SnapCreateSerializer（作成に失敗したとき）
# =========================================================
def remove_physical_file(path):
    full_path = full_path_of(path)
    if os.path.exists(full_path):
        os.remove(full_path)


# =========================================================
# delete_file：File の実ファイルと DB の行を消す
# - 受け取るもの：file_obj（File。None なら何もしない）
# - 返すもの    ：なし
# - 実ファイルは、File の行が消えたときに signals.py でも消される（管理画面から消した場合など）
#   ここで先に消しても、あとから消そうとしても、どちらも「無ければ何もしない」ので問題ない
# =========================================================
def delete_file(file_obj):
    # ① file_obj がなければ何もしない
    if not file_obj:
        return

    # ② 実ファイルを消す
    remove_physical_file(file_obj.path)

    # ③ DB の行を消す
    File.objects.filter(id=file_obj.id).delete()
