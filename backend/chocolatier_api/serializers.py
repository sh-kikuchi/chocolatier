from rest_framework import serializers #シリアライザーをインポート
from .models import Snap, User, File
from .models import File
from datetime import datetime
import os

# =========================================================
# スナップモデルの一覧表示用シリアライザー
# - get: 一覧取得：/snaps/
# - get: 詳細取得：/snaps/1/
# - putch: 更新：/snaps/1/ ※この時ファイル情報は更新しない
# =========================================================
class SnapSerializer(serializers.ModelSerializer):
    filePath = serializers.CharField(source='file.path', read_only=True)

    class Meta:
        model = Snap
        fields = ['id', 'file', 'filePath', 'comment', 'created_at', 'updated_at']

# =========================================================
# スナップモデルの新規作成用シリアライザー
# =========================================================
class SnapCreateSerializer(serializers.ModelSerializer):
    upload = serializers.FileField(write_only=True)  # 新規作成時に必須
    filePath = serializers.CharField(source='file.path', read_only=True)  # レスポンス用に追加

    class Meta:
        model = Snap
        # - file は upload から自動生成
        # - user はフロントから受け取らない（views.py の SnapCreate.perform_create で
        #   ログインユーザーを渡す）。受け取るとなりすまし投稿ができてしまうため
        fields = ['id', 'comment', 'upload', 'filePath']

    def create(self, validated_data):
        upload = validated_data.pop('upload')

        # FileUploadSerializer を使ってファイル保存
        file_serializer = FileUploadSerializer(data={'upload': upload})
        file_serializer.is_valid(raise_exception=True)
        file_obj = file_serializer.save()

        # Snap 作成
        snap = Snap.objects.create(file=file_obj, **validated_data)
        return snap

# =========================================================
# スナップ更新用シリアライザー
# -
# =========================================================
class SnapUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Snap
        fields = ['comment']  # コメントだけ更新

# =========================================================
# スナップ削除用シリアライザー
# =========================================================
class SnapDeleteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Snap
        fields = ['id', 'file', 'comment', 'created_at', 'updated_at']

    def delete(self, instance):
        import os
        from django.conf import settings

        # 1. Snap に紐づく File を先に取得
        file_obj = instance.file
        print("DEBUG: Snap ID:", instance.id)
        print("DEBUG: File object:", file_obj)

        if file_obj:
            # 2. 実ファイルパス確認
            full_path = os.path.join(settings.MEDIA_ROOT, file_obj.path.replace("\\","/"))
            print("DEBUG: Full file path:", full_path)
            print("DEBUG: File exists?", os.path.exists(full_path))

        # 3. Snap 削除
        instance.delete()
        print("DEBUG: Snap deleted")

        # 4. File 削除は FileDeleteSerializer に委譲
        if file_obj:
            print("DEBUG: Calling FileDeleteSerializer.delete_file()")
            FileDeleteSerializer.delete_file(file_obj)
            print("DEBUG: FileDeleteSerializer finished")

        return {"message": f"Snap {instance.id} and related file deleted successfully."}

# =========================================================
# ユーザーモデルのシリアライザー
# =========================================================
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password',)
        #パスワードフィールドを書き込み専用にする
        extra_kwargs = {'password':{'write_only': True}}
    
    #create時にcreate_userメソッドを使用
    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

# =========================================================
# ファイルモデルのシリアライザー()
# =========================================================
class FileUploadSerializer(serializers.ModelSerializer):
    upload = serializers.FileField(write_only=True, required=True)

    class Meta:
        model = File
        fields = ['id', 'name', 'path', 'created_at', 'updated_at', 'upload']
        read_only_fields = ['id', 'path', 'created_at', 'updated_at']

    def create(self, validated_data):
        upload = validated_data.pop('upload')
        original_name, ext = os.path.splitext(upload.name)

        # 現在日時を yyyymmddHHMMSS 形式で取得
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        # 新しいファイル名
        new_filename = f"{original_name}_{timestamp}{ext}"

        # 保存先パス
        from django.conf import settings
        save_path = os.path.join("uploads", new_filename)  # media/uploads/filename

        # 実際に保存
        full_path = os.path.join(settings.MEDIA_ROOT, save_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb+") as f:
            for chunk in upload.chunks():
                f.write(chunk)

        # DB保存
        file_obj = File.objects.create(
            name=validated_data.get("name") or new_filename,
            path=save_path
        )
        return file_obj

class FileDeleteSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = []

    @staticmethod
    def delete_file(file_obj):
        import os
        from django.conf import settings

        if not file_obj:
            print("DEBUG: No file_obj to delete")
            return

        full_path = os.path.join(settings.MEDIA_ROOT, file_obj.path.replace("\\","/"))
        print("DEBUG: Deleting file at path:", full_path)

        if os.path.exists(full_path):
            os.remove(full_path)
            print("DEBUG: File removed from disk")
        else:
            print("DEBUG: File does not exist on disk")

        # DB 削除
        File.objects.filter(id=file_obj.id).delete()
        print("DEBUG: File deleted from DB")