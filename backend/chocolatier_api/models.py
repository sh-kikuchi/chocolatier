from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings  # Snapモデルで使用するため必須

# =========================================================
# Snapモデル
# - ユーザーとファイルに紐づくスナップ情報を管理
# =========================================================
class Snap(models.Model):
    id = models.BigAutoField(primary_key=True)  # BIGINT 主キー、自動採番
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # カスタムユーザーに紐付け
        on_delete=models.CASCADE,  # ユーザー削除時にスナップも削除
        related_name='snaps'       # user.snaps で逆参照可能
    )
    file = models.ForeignKey(
        'File',                     # Fileモデルに紐付け（文字列で指定すると順序の制約が緩和）
        on_delete=models.CASCADE,    # ファイル削除時にスナップも削除
        related_name='snaps'         # file.snaps で逆参照可能
    )
    comment = models.TextField(blank=True, null=True)  # コメントは任意
    created_at = models.DateTimeField(auto_now_add=True)  # 作成日時（自動）
    updated_at = models.DateTimeField(auto_now=True)      # 更新日時（自動）

    def __str__(self):
        # 管理画面やシェルで見やすい表示
        return f"{self.id} - {self.user.username} - {self.file.name}"


# =========================================================
# カスタムユーザーモデル
# - username: テキストフィールドに変更、ユニーク
# - first_name / last_name: 不要のため削除
# =========================================================
class User(AbstractUser):
    # デフォルトのCharFieldからTextFieldに変更
    username = models.TextField(unique=True)  

    # 不要フィールドを削除
    first_name = None
    last_name = None

    def __str__(self):
        # 管理画面やprintで表示される文字列表現
        return self.username

# =========================================================
# Fileモデル
# =========================================================
class File(models.Model):
    id = models.BigAutoField(primary_key=True)  # BIGINT 主キー
    name = models.CharField(max_length=255, blank=True, null=True)  # ファイル名（任意）
    path = models.CharField(max_length=500, unique=True) # ファイルパス（ユニーク推奨）
    created_at = models.DateTimeField(auto_now_add=True) # 登録日時（自動）
    updated_at = models.DateTimeField(auto_now=True) # 更新日時（自動）

    def __str__(self):
        # ファイル名があれば表示、なければID表示
        return self.name or str(self.id)
