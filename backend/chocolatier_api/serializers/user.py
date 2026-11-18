# =========================================================
# serializers/user.py
# - ユーザーの翻訳係（新規登録・ログイン中の情報）
# =========================================================
from rest_framework import serializers

from ..models import User

# =========================================================
# ユーザーモデルのシリアライザー
# =========================================================
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password',)
        # パスワードフィールドを書き込み専用にする
        extra_kwargs = {'password': {'write_only': True}}

    # メールアドレスの重複チェック（改修案件08）
    # - 大文字・小文字の違いだけのアドレスも同じとみなす（iexact）
    # - メールアドレスは任意のまま。空のときは重複を見ない（空の人が何人いてもよい）
    # - DB の一意制約にしないのは、空のメールアドレスの利用者が複数いても登録できるようにするため
    def validate_email(self, value):
        if value and User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('このメールアドレスはすでに登録されています')
        return value

    # create 時に create_user メソッドを使用（パスワードをハッシュ化して保存するため）
    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user
