# =========================================================
# views/（API の「窓口」を置くフォルダ）
# - urls.py で URL とクラスが結びつけられ、リクエストが来るとクラスの get / post などが呼ばれる
# - 以前は views.py 1 ファイルにすべてあったが、役割ごとにファイルを分けた（改修案件7）
#     snap.py … Snap（一覧・詳細・作成・Zip ダウンロード）
#     tag.py  … タグ（絞り込みの候補）
#     user.py … ユーザー（新規登録・ログイン中の情報）
#     auth.py … 認証（ログイン・refresh・ログアウト・CSRF）
#     media.py … 画像の配信（ログインしている持ち主だけ。改修案件08）
# - 認証（誰か？）と権限（使ってよいか？）は settings.py の REST_FRAMEWORK で
#   全 API 共通に設定済み。例外にしたい View だけ、クラス変数で上書きする
#     - authentication_classes : 認証クラス（Cookie の JWT を読むかどうか）
#     - permission_classes     : 権限クラス（ログイン必須かどうか）
#
# このファイルの役割
# - 各ファイルのクラスをここで import し直して、views の「表札」にする
#   → urls.py の `from .views import SnapList` のような書き方が、分ける前と同じまま動く
# - __all__：外から使ってよい名前の一覧（`from .views import *` で読まれる名前。
#   また「ここで import したのは使うためではなく、外に出すため」と読む人に伝える）
# =========================================================
from .auth import CookieLoginView, CookieRefreshView, CsrfView, LogoutView, set_auth_cookies
from .media import MediaFileView
from .snap import SnapCreate, SnapDetail, SnapList, SnapZipDownload
from .tag import TagList
from .user import UserInfoView, UserSignup

__all__ = [
    # snap.py
    'SnapList',
    'SnapDetail',
    'SnapCreate',
    'SnapZipDownload',
    # tag.py
    'TagList',
    # user.py
    'UserSignup',
    'UserInfoView',
    # auth.py
    'set_auth_cookies',
    'CookieLoginView',
    'CookieRefreshView',
    'LogoutView',
    'CsrfView',
    # media.py
    'MediaFileView',
]
