# =========================================================
# views/media.py（改修案件08）
# - 画像の配信の窓口：GET /media/<path>
# - 以前は Django 標準の static()（DEBUG のときだけ動く、誰でも見られる配信）を使っていたため、
#   URL を知っていればログインしなくても画像が見られた
# - 今は「ログインしている持ち主」にだけ返す
#   - 未ログイン               → 401（settings.py の共通設定：ログイン必須）
#   - 他人の画像・存在しない画像 → 404（存在すること自体を知らせない。Snap の API と同じ考え方）
# - フロントの <img src="http://localhost:8000/media/..."> は、ブラウザが Cookie（access_token）を
#   自動で付けて送るので、フロント側の変更はいらない
#   （localhost:3000 と localhost:8000 は「同じサイト」なので、SameSite=Lax の Cookie も送られる）
# =========================================================
import mimetypes                                                   # 拡張子から Content-Type を決める
import os

from django.http import FileResponse                               # ファイルを少しずつ送るレスポンス
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import File
from ..services.files import full_path_of


class MediaFileView(APIView):
    def get(self, request, file_path):
        # ① 自分のスナップの画像だけを探す
        #    - file_path は URL の /media/ より後ろ（例：uploads/photo_20261001120000.jpg）
        #    - Windows で保存した path は「uploads\photo...jpg」の形のこともあるので、両方の形で探す
        #    - DB に登録されている path だけを返すので、「../」などで別の場所のファイルを読まれることはない
        file_obj = (
            File.objects
            .filter(path__in=[file_path, file_path.replace('/', '\\')], snaps__user=request.user)
            .first()
        )
        if file_obj is None:
            return Response({"detail": "見つかりませんでした。"}, status=status.HTTP_404_NOT_FOUND)

        # ② 実ファイルがなければ 404
        full_path = full_path_of(file_obj.path)
        if not os.path.exists(full_path):
            return Response({"detail": "見つかりませんでした。"}, status=status.HTTP_404_NOT_FOUND)

        # ③ 画像を返す（as_attachment を付けないので、ブラウザはその場で表示する）
        content_type = mimetypes.guess_type(full_path)[0] or 'application/octet-stream'
        return FileResponse(open(full_path, 'rb'), content_type=content_type)
