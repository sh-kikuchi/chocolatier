# =========================================================
# views/auth.py
# - 認証の窓口：ログイン・トークンの取り直し・ログアウト・CSRF Cookie の配布
# - どれも未ログイン（または期限切れ）の状態で呼ばれるため、
#   authentication_classes = [] / AllowAny で共通設定を上書きしている
# - URL は chocolatier_core/urls.py で登録（/token/ など、/chocolatier_api/ の外）
# =========================================================
from django.conf import settings                                   # settings.py の値（Cookie 名・有効期限など）
from django.utils.decorators import method_decorator               # 関数用デコレーターをクラスに付けるため
from django.views.decorators.csrf import ensure_csrf_cookie        # csrftoken Cookie を必ず発行するデコレーター
from rest_framework import status                                  # HTTP ステータスコード
from rest_framework.exceptions import AuthenticationFailed         # 認証失敗の例外（パスワード違いなど）
from rest_framework.permissions import AllowAny                    # AllowAny: 誰でも可
from rest_framework.response import Response                       # API のレスポンス（JSON）を返すクラス
from rest_framework.views import APIView                           # 自分で get / post を書く基本の View
from rest_framework_simplejwt.exceptions import TokenError         # JWT が不正・期限切れのときの例外
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer  # ログイン用 / refresh 用のトークン発行処理

# =========================================================
# 認証 Cookie の共通処理
# - ログイン時と refresh 時の両方で使うので関数にまとめている
# - access  : API を呼ぶときに使うトークン（有効期限 60 分）
# - refresh : access を取り直すためのトークン（有効期限 1 日）
#             refresh 時は新しい refresh が発行されないことがあるので省略可能
# =========================================================
def set_auth_cookies(response, access, refresh=None):
    # 2 つの Cookie に共通のオプション
    cookie_options = {
        'httponly': True,                           # JS（document.cookie）から読めない → XSS でトークンを盗まれない
        'secure': settings.AUTH_COOKIE_SECURE,      # True なら HTTPS のときだけ送る（開発は http なので False）
        'samesite': settings.AUTH_COOKIE_SAMESITE,  # 'Lax' : 別サイトからの POST などでは送らない（CSRF の軽減）
        'path': '/',                                # どの URL へのリクエストでも送る
    }

    # access_token の Cookie
    # - max_age（秒）をトークンの有効期限に合わせ、期限が切れたらブラウザからも消えるようにする
    response.set_cookie(
        settings.AUTH_COOKIE_ACCESS,
        access,
        max_age=int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()),
        **cookie_options  # 上の辞書をキーワード引数として展開する
    )

    # refresh_token の Cookie（渡されたときだけ）
    if refresh:
        response.set_cookie(
            settings.AUTH_COOKIE_REFRESH,
            refresh,
            max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),
            **cookie_options
        )

# =========================================================
# CookieLoginView
# - post: ログイン。トークンは Cookie にセットし、本文には含めない
# - authentication_classes = [] にしないと、期限切れ Cookie が残っているだけで 401 になる
#   （DRF はどの View でも、処理の前に必ず認証を実行するため）
# - URL: /token/（chocolatier_core/urls.py で登録）
# =========================================================
class CookieLoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        # simplejwt 標準のログイン処理
        # - username / password を検証し、正しければ access と refresh を発行する
        serializer = TokenObtainPairSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except (AuthenticationFailed, TokenError):
            # パスワード違いなど
            # - 「ユーザー名」と「パスワード」のどちらが違うかは、あえて教えない
            #   （存在するユーザー名を推測されないようにするため）
            return Response(
                {"detail": "ユーザー名またはパスワードが違います"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # 本文にはトークンを入れない（JS に渡さない）
        response = Response({"message": "ログインしました"}, status=status.HTTP_200_OK)
        # トークンは Cookie に入れて返す → 以降はブラウザが自動で送ってくれる
        set_auth_cookies(
            response,
            serializer.validated_data['access'],
            serializer.validated_data['refresh']
        )
        return response

# =========================================================
# CookieRefreshView
# - post: Cookie の refresh から新しい access を発行する
# - フロントの client.ts が、API で 401 を受けたときに自動で呼ぶ
# - URL: /token/refresh/
# =========================================================
class CookieRefreshView(APIView):
    # access が期限切れの状態で呼ばれる API なので、認証は外す
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        # ① Cookie から refresh_token を取り出す（JS は触れないので、本文ではなく Cookie から読む）
        refresh = request.COOKIES.get(settings.AUTH_COOKIE_REFRESH)
        if refresh is None:
            # refresh も無い（1 日以上経った・ログアウト済み）→ 再ログインが必要
            return Response({"detail": "refresh token がありません"}, status=status.HTTP_401_UNAUTHORIZED)

        # ② simplejwt 標準の refresh 処理で、新しい access を発行する
        serializer = TokenRefreshSerializer(data={'refresh': refresh})
        try:
            serializer.is_valid(raise_exception=True)
        except (AuthenticationFailed, TokenError):
            # refresh が期限切れ・改ざん、またはユーザーが無効化されている
            return Response({"detail": "refresh token が無効です"}, status=status.HTTP_401_UNAUTHORIZED)

        # ③ 新しい access（と、発行されていれば新しい refresh）を Cookie に入れ直す
        response = Response({"message": "トークンを更新しました"}, status=status.HTTP_200_OK)
        set_auth_cookies(
            response,
            serializer.validated_data['access'],
            serializer.validated_data.get('refresh')  # ローテーション無効時は None
        )
        return response

# =========================================================
# LogoutView
# - post: 認証 Cookie を削除する
# - HttpOnly Cookie は JS から消せないので、サーバーに消してもらう必要がある
# - URL: /logout/
# =========================================================
class LogoutView(APIView):
    # access が期限切れでもログアウトできるように、認証は外す
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        response = Response({"message": "ログアウトしました"}, status=status.HTTP_200_OK)
        # set_cookie と同じ path / samesite を指定しないと、別の Cookie 扱いになって消えない
        response.delete_cookie(settings.AUTH_COOKIE_ACCESS, path='/', samesite=settings.AUTH_COOKIE_SAMESITE)
        response.delete_cookie(settings.AUTH_COOKIE_REFRESH, path='/', samesite=settings.AUTH_COOKIE_SAMESITE)
        return response

# =========================================================
# CsrfView
# - get: csrftoken Cookie を配布する（フロント起動時に呼ぶ）
# - csrftoken は HttpOnly ではない Cookie なので、JS（axios）が読める
#   → axios が値を X-CSRFToken ヘッダーにコピーして送る
#   → authentication.py の enforce_csrf が、Cookie とヘッダーの一致を確かめる
# - URL: /csrf/
# =========================================================
# ensure_csrf_cookie は関数用のデコレーターなので、method_decorator で
# クラスの dispatch（全メソッドの入口）に付ける
@method_decorator(ensure_csrf_cookie, name='dispatch')
class CsrfView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"message": "CSRF cookie set"})
