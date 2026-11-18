# =========================================================
# serializers/（「翻訳係」を置くフォルダ）
# - JSON ⇔ Python の変換と、入力チェックを担当する
# - 以前は serializers.py 1 ファイルにすべてあったが、役割ごとにファイルを分けた（改修案件7）
#     snap.py … Snap（一覧・作成・更新・削除・Zip）とタグの共通処理
#     user.py … ユーザー
#   ※ 画像ファイルの保存・削除は services/files.py に移した（改修案件7 M5）
#
# このファイルの役割
# - 各ファイルのクラスをここで import し直して、serializers の「表札」にする
#   → views の `from ..serializers import SnapSerializer` のような書き方が、そのまま使える
# =========================================================
from .snap import (
    SnapCreateSerializer,
    SnapDeleteSerializer,
    SnapSerializer,
    SnapUpdateSerializer,
    SnapZipDownloadSerializer,
    clean_tag_names,
    set_snap_tags,
)
from .user import UserSerializer

__all__ = [
    # snap.py
    'clean_tag_names',
    'set_snap_tags',
    'SnapSerializer',
    'SnapCreateSerializer',
    'SnapUpdateSerializer',
    'SnapDeleteSerializer',
    'SnapZipDownloadSerializer',
    # user.py
    'UserSerializer',
]
