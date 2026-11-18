# =========================================================
# views/tag.py
# - タグの窓口：絞り込みの候補（自分の Snap に付いているタグ）
# =========================================================
from rest_framework.response import Response                       # API のレスポンス（JSON）を返すクラス
from rest_framework.views import APIView                           # 自分で get / post を書く基本の View

from ..models import Tag

# =========================================================
# TagList
# - get: 自分の Snap に付いているタグ一覧：/tags/（例：["カフェ", "旅行"]）
# =========================================================
class TagList(APIView):
    def get(self, request):
        # ① 自分の Snap に付いているタグだけ（他の人のタグは出さない）
        # ② distinct：同じタグが複数の Snap に付いていても 1 つにする
        # ③ values_list：名前だけの配列にする
        names = (
            Tag.objects
            .filter(snaps__user=request.user)
            .distinct()
            .values_list('name', flat=True)
        )
        return Response(list(names))
