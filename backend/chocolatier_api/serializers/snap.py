# =========================================================
# serializers/snap.py
# - Snap（投稿）の翻訳係：一覧・詳細の形、作成・更新・削除、Zip ダウンロードの入力チェック
# - タグの共通処理（clean_tag_names / set_snap_tags）もここに置く（Snap の作成・更新でだけ使うため）
# =========================================================
from django.conf import settings                             # settings.py の上限値を読むため
from django.core.validators import FileExtensionValidator    # 拡張子チェック用の Django 標準バリデーター
from django.db import transaction                            # 作成をまとめて 1 つの処理にする（途中で失敗したら全部取り消す）
from rest_framework import serializers

from ..models import Snap, Tag
from ..services.files import remove_physical_file, save_upload  # 画像ファイルの保存・後片付け（作業係）
from ..services.tags import delete_unused_tags                 # 使われていないタグの片付け（作業係）

# =========================================================
# タグの共通処理（作成・更新の両方で使う）
# =========================================================

# ---------------------------------------------------------
# clean_tag_names：受け取ったタグ名の配列を整えて、チェックする
# - 例：[" 旅行", "カフェ", "", "旅行"] → ["旅行", "カフェ"]
# - NG なら ValidationError を発生させる（→ 400 で {"tags": ["..."]} が返る）
# ---------------------------------------------------------
def clean_tag_names(names):
    # 整えた結果を入れる箱
    cleaned = []

    for name in names:
        # 前後の空白を除く（" 旅行 " → "旅行"）
        name = name.strip()

        # 空のタグは捨てて、次のタグへ
        #（空白だけのタグや、フロントが空文字を送ってきた場合）
        if not name:
            continue

        # タグの文字数をチェック（settings.py の MAX_TAG_LENGTH = 30）
        # どのタグが長いのか分かるように、メッセージにタグ名を入れる
        if len(name) > settings.MAX_TAG_LENGTH:
            raise serializers.ValidationError(
                f'タグ「{name}」が長すぎます。{settings.MAX_TAG_LENGTH}文字以内にしてください'
            )

        # 重複を除く：まだ箱に入っていないタグだけ追加する
        if name not in cleaned:
            cleaned.append(name)

    # タグの個数をチェック（settings.py の MAX_TAGS_PER_SNAP = 10）
    # 空のタグと重複を除いた「後」の個数で数える
    if len(cleaned) > settings.MAX_TAGS_PER_SNAP:
        raise serializers.ValidationError(f'タグは{settings.MAX_TAGS_PER_SNAP}個までにしてください')

    # 整えた配列を返す（これが validated_data['tags'] になる）
    return cleaned

# ---------------------------------------------------------
# set_snap_tags：Snap に付いているタグを、names の内容に入れ替える
# - 例：今「旅行」が付いている Snap に ["カフェ"] を渡す → 「カフェ」だけになる
# - 空の配列 [] を渡すと、タグをすべて外す
# ---------------------------------------------------------
def set_snap_tags(snap, names):
    # ① タグ名から Tag オブジェクトを用意する
    #    get_or_create：その名前のタグがあれば取得、なければ作成する
    #    戻り値は (タグ, 新しく作ったかどうか) のタプルなので、[0] でタグだけ取り出す
    tags = [Tag.objects.get_or_create(name=name)[0] for name in names]

    # ② 中間テーブル（snap_tags）を、①のタグの組み合わせに入れ替える
    #    set()：足りないものは追加し、余分なものは削除してくれる
    snap.tags.set(tags)

    # ③ どのスナップにも付いていないタグを消す（改修案件08）
    #    - 外したタグが、ほかのスナップ（ほかの利用者のものも含む）で使われていなければ消える
    delete_unused_tags()

# =========================================================
# スナップモデルの一覧表示用シリアライザー
# - get: 一覧取得：/snaps/
# - get: 詳細取得：/snaps/1/
# - 作成・更新のレスポンスも、この形で返す
# =========================================================
class SnapSerializer(serializers.ModelSerializer):
    filePath = serializers.CharField(source='file.path', read_only=True)

    # tags：付いているタグを、名前の配列で返す（例：["カフェ", "旅行"]）
    # - SlugRelatedField：関連先のオブジェクトを、その 1 つの項目（slug_field）で表す
    # - many=True：多対多なので配列になる
    # - read_only=True：このシリアライザーは表示専用（受け取りは作成・更新用で行う）
    tags = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')

    class Meta:
        model = Snap
        fields = ['id', 'file', 'filePath', 'comment', 'tags', 'created_at', 'updated_at']

# =========================================================
# スナップモデルの新規作成用シリアライザー
# =========================================================
class SnapCreateSerializer(serializers.ModelSerializer):
    upload = serializers.ImageField(
        write_only=True,  # 受け取るだけで、レスポンスには含めない
        validators=[FileExtensionValidator(allowed_extensions=settings.ALLOWED_IMAGE_EXTENSIONS)],
    )
    filePath = serializers.CharField(source='file.path', read_only=True)  # レスポンス用に追加

    # ---------------------------------------------------------
    # tags：付けるタグ名の配列（任意）
    # - ListField：配列を受け取る。child は配列の 1 要素の型
    # - 作成は multipart で送るので、フロントは tags を同じキーで繰り返し送る
    #   （tags=旅行 & tags=カフェ → ["旅行", "カフェ"]）
    # - allow_blank=True：空文字もいったん受け取り、validate_tags で捨てる
    # - required=False：送らなければタグなし
    # - write_only=True：返すときは to_representation で SnapSerializer の tags を使う
    # ---------------------------------------------------------
    tags = serializers.ListField(
        child=serializers.CharField(allow_blank=True),
        required=False,
        write_only=True,
    )

    class Meta:
        model = Snap
        # - file は upload から自動生成
        # - user はフロントから受け取らない（views/snap.py の SnapCreate.perform_create で
        #   ログインユーザーを渡す）。受け取るとなりすまし投稿ができてしまうため
        fields = ['id', 'comment', 'upload', 'filePath', 'tags']
        # extra_kwargs：モデルから自動で作られるフィールドに、オプションを追加する
        # - comment はモデルが TextField（上限なし）なので、ここで最大文字数を付ける
        # - 超えると「この値は 1000 文字以下でなければなりません。」のようなエラーになる
        extra_kwargs = {
            'comment': {'max_length': settings.MAX_COMMENT_LENGTH},
        }

    # ---------------------------------------------------------
    # validate_<フィールド名>：そのフィールドだけの独自チェック（チェック順 ③）
    # - value には、①② を通過した後の値（アップロードされたファイル）が入る
    # - 問題があれば ValidationError を発生させる → 400 で {"upload": ["..."]} が返る
    # - 問題がなければ、value をそのまま return する（return を忘れると None になる）
    # ---------------------------------------------------------
    def validate_upload(self, value):
        # value.size：ファイルサイズ（バイト）
        if value.size > settings.MAX_UPLOAD_SIZE:
            max_mb = settings.MAX_UPLOAD_SIZE // (1024 * 1024)  # 表示用に MB に直す
            raise serializers.ValidationError(f'画像サイズは{max_mb}MB以下にしてください')
        return value

    # tags のチェック
    def validate_tags(self, value):
        return clean_tag_names(value)

    def create(self, validated_data):
        upload = validated_data.pop('upload')
        # tags は Snap の「列」ではない（中間テーブルに入る）ので、先に取り出しておく
        # - 取り出さずに Snap.objects.create(tags=...) に渡すと、
        #   「多対多には直接代入できない」という TypeError になる
        tag_names = validated_data.pop('tags', [])

        # 画像の保存・Snap の作成・タグ付けを、1 つの処理（トランザクション）にまとめる（改修案件08）
        # - transaction.atomic：中で失敗したら、DB への変更を全部取り消す（File の行だけが残らない）
        # - 実ファイルは DB ではないので取り消されない → 失敗したら自分で消す
        file_obj = None
        try:
            with transaction.atomic():
                # ① 画像ファイルを保存して、File（DB の行）を作る（services/files.py の save_upload）
                file_obj = save_upload(upload)

                # ② Snap 作成
                snap = Snap.objects.create(file=file_obj, **validated_data)

                # ③ Snap が DB に保存されて id ができてから、タグを付ける
                #    （中間テーブルには snap_id が必要なため、create より前には付けられない）
                set_snap_tags(snap, tag_names)
        except Exception:
            # ④ 途中で失敗したら、保存した実ファイルを消してから、失敗をそのまま伝える
            if file_obj is not None:
                remove_physical_file(file_obj.path)
            raise
        return snap

    # 返すときの形
    # - 一覧・詳細（SnapSerializer）と同じ形で返す
    #   → フロントは、作成した Snap をそのまま一覧に追加できる
    def to_representation(self, instance):
        return SnapSerializer(instance, context=self.context).data

# =========================================================
# スナップ更新用シリアライザー
# - コメントとタグを更新する（画像は変えない）
# =========================================================
class SnapUpdateSerializer(serializers.ModelSerializer):
    # tags：付けるタグ名の配列（作成と同じ）
    # - 更新は JSON で送るので、["旅行", "カフェ"] の配列をそのまま送る
    # - 空の配列 [] を送ると、タグをすべて外す
    tags = serializers.ListField(
        child=serializers.CharField(allow_blank=True),
        required=False,
        write_only=True,
    )

    class Meta:
        model = Snap
        fields = ['comment', 'tags']  # コメントとタグを更新（画像は変えない）
        # 新規作成（SnapCreateSerializer）と同じ上限にする
        extra_kwargs = {
            'comment': {'max_length': settings.MAX_COMMENT_LENGTH},
        }

    def validate_tags(self, value):
        return clean_tag_names(value)

    def update(self, instance, validated_data):
        # None：tags が送られてこなかった（PATCH で comment だけ送った）
        # []  ：タグを全部外したい
        # この 2 つを区別するため、pop の既定値を None にする
        tag_names = validated_data.pop('tags', None)

        # comment など、普通の列の更新は親クラス（ModelSerializer）に任せる
        instance = super().update(instance, validated_data)

        if tag_names is not None:
            set_snap_tags(instance, tag_names)
        return instance

    # 返すときの形も一覧・詳細と同じにする（以前は {"comment": ...} だけだった）
    def to_representation(self, instance):
        return SnapSerializer(instance, context=self.context).data

# =========================================================
# スナップ削除用シリアライザー
# =========================================================
class SnapDeleteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Snap
        fields = ['id', 'file', 'comment', 'created_at', 'updated_at']

    def delete(self, instance):
        # Snap を消す
        # - 画像（File の行と実ファイル）と、使われなくなったタグの後片付けは signals.py が行う（改修案件08）
        #   → 管理画面や利用者の削除から消したときも、同じ後片付けが動く
        instance.delete()

# =========================================================
# Zip ダウンロード用シリアライザー
# - POST /chocolatier_api/snap/download/ で受け取る値をチェックするだけ
# - DB に保存しないので ModelSerializer ではなく Serializer を使う
#   （モデルがないため、フィールドは自分で 1 つずつ宣言する）
# =========================================================
class SnapZipDownloadSerializer(serializers.Serializer):
    # ① ids：Zip に入れる Snap の ID の配列（必須）
    #    - child：配列の 1 要素の型（整数）
    #    - min_length=1：空の配列はダメ
    #    - max_length：上限 100 件（settings.py の MAX_ZIP_DOWNLOAD）
    ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=settings.MAX_ZIP_DOWNLOAD,
    )

    # ② tag：Zip の中のフォルダ名に使うタグ名（任意）
    #    - required=False：「すべて」のときは送らない
    #    - max_length：タグ名の上限と同じ 30 文字
    tag = serializers.CharField(
        required=False,
        max_length=settings.MAX_TAG_LENGTH,
    )
