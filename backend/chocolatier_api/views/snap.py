# =========================================================
# views/snap.py
# - Snap（投稿）の窓口：一覧・詳細・更新・削除・作成・Zip ダウンロード
# - 認証・権限は settings.py の REST_FRAMEWORK の共通設定（ログイン必須）を使う
# =========================================================
from django.http import FileResponse                               # ファイルをダウンロードさせるレスポンス
from rest_framework import generics, status                        # generics: 一覧・詳細などの定型 View / status: HTTP ステータスコード
from rest_framework.response import Response                       # API のレスポンス（JSON）を返すクラス
from rest_framework.views import APIView                           # 自分で get / post を書く基本の View

# 「..」は 1 つ上のフォルダ（chocolatier_api）。このファイルは views/ の中にあるため
from ..models import Snap
from ..pagination import SnapCursorPagination
from ..serializers import (
    SnapSerializer,
    SnapCreateSerializer,
    SnapUpdateSerializer,
    SnapDeleteSerializer,
    SnapZipDownloadSerializer,
)
from ..services.zip import build_snap_zip, safe_folder_name

# =========================================================
# SnapList
# - get: 一覧取得：/snaps/
# - ログインユーザー自身のスナップのみ、新しい順で返す
# - permission_classes を書いていないので、settings.py の
#   IsAuthenticated（ログイン必須）が適用される
# =========================================================
class SnapList(generics.ListAPIView):
    serializer_class = SnapSerializer

    # 12 件ずつ返す（pagination.py の SnapCursorPagination）
    # - レスポンスが配列から { next, previous, results } の形に変わる
    # - ?tag=〇〇 は next の URL にそのまま引き継がれる（絞り込んだまま続きを取れる）
    pagination_class = SnapCursorPagination

    # 一覧に出すデータを決めるメソッド
    def get_queryset(self):
        # ① 自分の Snap を新しい順で取得（File と tags はまとめて取得して N+1 を防ぐ）
        #    - self.request.user は、Cookie の JWT から特定したログインユーザー
        queryset = (
            Snap.objects
            .filter(user=self.request.user)
            .select_related('file')   # 多対1：JOIN で一緒に取る
            .prefetch_related('tags') # 多対多：別の SQL 1 回で取る
            .order_by('-created_at')
        )

        # ② URL の ?tag=〇〇 を読む（例：/snaps/?tag=旅行 → "旅行"、指定なしなら None）
        tag = self.request.query_params.get('tag')

        # ③ tag が指定されていたら、そのタグが付いた Snap だけに絞る
        #    - tags__name：Snap → tags → name の順にたどる（__ で関連先の項目を指定する）
        if tag:
            queryset = queryset.filter(tags__name=tag)

        return queryset

# =========================================================
# SnapDetail
# - get: 詳細取得
# - patch: 更新（ファイルは更新しない）
# - delete: 削除
# - 他人のスナップは get_queryset に含まれないため 404 になる
# =========================================================
class SnapDetail(generics.RetrieveUpdateDestroyAPIView):
    # 受け付ける HTTP メソッド（改修案件08）
    # - RetrieveUpdateDestroyAPIView は PUT（全体の置き換え）も受け付けるが、画面では使っていないので受け付けない
    #   → 使っていないメソッドは開けておかない方針。PUT は 405（Method Not Allowed）になる
    # - head / options は、ブラウザや DRF が使う補助のメソッドなので残す
    http_method_names = ['get', 'patch', 'delete', 'head', 'options']

    # 取得・更新・削除の対象になるデータの範囲
    # - URL の <int:pk> は、この範囲の中から探される
    # - 他人の Snap の ID を指定しても「見つからない」＝ 404 になる
    #   （403 にしないのは「その ID の投稿が存在すること」自体を知らせないため）
    def get_queryset(self):
        return Snap.objects.filter(user=self.request.user)

    # HTTP メソッドごとに使うシリアライザーを切り替える
    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return SnapUpdateSerializer   # コメントとタグを更新
        elif self.request.method == 'DELETE':
            return SnapDeleteSerializer   # 実ファイルも一緒に削除
        return SnapSerializer             # GET（詳細表示）

    def destroy(self, request, *args, **kwargs):
        # get_object() も get_queryset() の範囲から探すので、他人の Snap なら 404
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        # ここで SnapDeleteSerializer.delete() を呼ぶ
        serializer.delete(instance)
        # 204 No Content：「成功したが、返す本文はない」という意味なので、本文は付けない（改修案件08）
        return Response(status=status.HTTP_204_NO_CONTENT)

# =========================================================
# SnapCreate
# - post: スナップ新規作成
# - 投稿者はフロントから受け取らず、ログインユーザーを使う
# =========================================================
class SnapCreate(generics.CreateAPIView):
    queryset = Snap.objects.all()
    serializer_class = SnapCreateSerializer

    # serializer.save() の直前に呼ばれるメソッド
    # - 以前はフロントが JWT を自分でデコードして user を送っていたため、
    #   値を書き換えれば「他人として投稿」できてしまった
    # - ここでサーバー側のログインユーザーを渡すことで、なりすましを防ぐ
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

# =========================================================
# SnapZipDownload
# - post: 表示中の Snap の画像を Zip にまとめて返す：/snap/download/
# - 本文：{ "ids": [12, 11, ...], "tag": "旅行" }（「すべて」のときは tag なし）
# - ids はフロントから送られてくるので、書き換えられる前提で扱う
#   → 自分の Snap だけに絞り、他人の ID は黙って除外する
# =========================================================
class SnapZipDownload(APIView):
    def post(self, request):
        # ① 受け取った値をチェックする
        serializer = SnapZipDownloadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data['ids']
        tag = serializer.validated_data.get('tag')  # 送られていなければ None

        # ② 自分の Snap だけを取得する
        #    - id__in：ids の配列に含まれる ID だけ
        #    - user=request.user：他人の Snap の ID が混ざっていても入らない
        #    - select_related('file')：画像のパスを取るときに SQL が増えないようにする
        snaps = (
            Snap.objects
            .filter(user=request.user, id__in=ids)
            .select_related('file')
            .order_by('-created_at')
        )

        # ③ 1 件もなければ 404
        #    - 他人の ID だけを送られたときもここに来る
        if not snaps.exists():
            return Response(
                {"detail": "ダウンロードできる画像がありません"},
                status=status.HTTP_404_NOT_FOUND
            )

        # ④ Zip の中のフォルダ名を決める（タグ名、なければ「すべて」。記号は「_」に置き換える）
        #    - 中身は services/zip.py の safe_folder_name
        folder_name = safe_folder_name(tag)

        # ⑤ 一時ファイルに Zip を書き込む
        #    - 中身は services/zip.py の build_snap_zip
        #    - added：Zip に入れた枚数。読む位置はもう先頭に戻してある
        zip_file, added = build_snap_zip(snaps, folder_name)

        # ⑤-2 1 枚も入らなかったら（実ファイルが全部消えていたら）404
        #      - 404 にするかどうかを決めるのは窓口（View）の仕事。一時ファイルは閉じて消しておく
        if added == 0:
            zip_file.close()
            return Response(
                {"detail": "ダウンロードできる画像がありません"},
                status=status.HTTP_404_NOT_FOUND
            )

        # ⑥ Zip を返す
        #    - as_attachment=True：ブラウザに「表示」ではなく「保存」させる
        #    - filename：日本語でも Django が自動でエンコードしてくれる
        #    - 送り終わると FileResponse がファイルを閉じる → 一時ファイルも消える
        return FileResponse(
            zip_file,
            as_attachment=True,
            filename=f'{folder_name}.zip',
            content_type='application/zip',
        )
