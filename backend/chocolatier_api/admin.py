from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, File, Snap

# =========================================================
# カスタムUserモデル用管理画面
# =========================================================
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    カスタムUserモデル管理画面設定
    - DjangoデフォルトのUserAdminを継承
    - 一覧表示、検索、フィルター、作成フォームの設定を追加
    """
    # 管理画面一覧で表示するカラム
    list_display = ('id', 'username', 'email', 'is_staff', 'is_active')
    
    # 検索バーで検索できるフィールド
    search_fields = ('username', 'email')
    
    # サイドバーでフィルタリングできるフィールド
    list_filter = ('is_staff', 'is_active', 'is_superuser')

    # ユーザー編集画面のフィールド構成
    fieldsets = (
        (None, {'fields': ('username', 'password', 'email')}),  # 基本情報
        ('権限', {'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),  # 権限関連
    )

    # ユーザー作成フォームのフィールド構成
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )

    # 一覧表示のデフォルト並び順
    ordering = ('id',)


# =========================================================
# Fileモデル用管理画面
# =========================================================
@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    """
    ファイル管理用管理画面設定
    - ファイル情報の一覧表示・検索・編集を簡単にする
    """
    # 管理画面一覧で表示するカラム
    list_display = ('id', 'name', 'path', 'created_at', 'updated_at')
    
    # 検索バーで検索できるフィールド
    search_fields = ('name', 'path')
    
    # 作成・更新日時は自動管理されるため編集不可に設定
    readonly_fields = ('created_at', 'updated_at')


# =========================================================
# Snapモデル用管理画面
# =========================================================
@admin.register(Snap)
class SnapAdmin(admin.ModelAdmin):
    """
    スナップ管理用管理画面設定
    - ユーザーとファイルに紐づくスナップ情報を管理
    - 外部キーのユーザー名・ファイル名で表示される
    """
    # 一覧表示するカラム
    list_display = ('id', 'user', 'file', 'comment', 'created_at', 'updated_at')
    
    # 検索バーで検索可能なフィールド
    # 外部キーの関連フィールドも __ で検索可能
    search_fields = ('comment', 'user__username', 'file__name')
    
    # 作成・更新日時は自動管理されるため編集不可
    readonly_fields = ('created_at', 'updated_at')
    
    # サイドバーでユーザー・ファイルで絞り込み可能
    list_filter = ('user', 'file')
