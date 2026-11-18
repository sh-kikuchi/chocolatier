# =========================================================
# views/user.py
# - ユーザーの窓口：新規登録（管理者だけ）・ログイン中のユーザー情報
# =========================================================
from rest_framework import status                                  # HTTP ステータスコード
from rest_framework.permissions import IsAuthenticated, IsAdminUser  # IsAuthenticated: ログイン必須 / IsAdminUser: 管理者だけ
from rest_framework.response import Response                       # API のレスポンス（JSON）を返すクラス
from rest_framework.views import APIView                           # 自分で get / post を書く基本の View

from ..serializers import UserSerializer

# =========================================================
# UserSignup
# - post: ユーザー新規登録
# - サインアップ画面は作らず、運用で Postman からユーザーを作るために使う
# - 管理者（is_staff=True のユーザー）だけが使える
#   - createsuperuser で作ったユーザーは is_staff=True
#   - この API で作ったユーザーは is_staff=False（一般ユーザー）
# - 以前は authentication_classes = [] / AllowAny で、誰でも登録できてしまっていた
# =========================================================
class UserSignup(APIView):
    # authentication_classes を書かない → settings.py の CookieJWTAuthentication が使われる
    #   （誰がリクエストしたかを知る必要があるため、認証は外さない）
    # IsAdminUser：
    #   - 未ログイン           → 401
    #   - ログイン中だが一般ユーザー → 403
    #   - ログイン中の管理者      → 登録できる
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "ユーザー登録が完了しました"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# =========================================================
# UserInfoView
# - get: ログイン中ユーザー情報取得
# - フロントは起動時・ログイン直後にこれを呼び、
#   「今ログインしているのは誰か」を AuthContext に保存する
# - Cookie が無い・期限切れなら 401 → フロントが refresh を試す
# =========================================================
class UserInfoView(APIView):
    # settings.py でも IsAuthenticated にしているが、意図を明確にするため明記
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
