from urllib import response
from django.shortcuts import render
from rest_framework import generics #ビューを作成するためのツールセット
from .models import Snap 
from .serializers import (
    SnapSerializer,
    SnapCreateSerializer,
    SnapUpdateSerializer,
    SnapDeleteSerializer,
    UserSerializer
)
from rest_framework import status 
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

# =========================================================
# SnapList
# - get: 一覧取得：/snaps/
# =========================================================
from rest_framework import generics
from .models import Snap
from .serializers import SnapSerializer

class SnapList(generics.ListAPIView):
    # 扱うクエリセットをSnapオブジェクト全てに設定
    queryset = Snap.objects.all()

    # シリアライザーを設定
    serializer_class = SnapSerializer

# =========================================================
# SnapDetail
# - get: 詳細取得
# - patch: 更新（ファイルは更新しない）
# - delete: 削除
# =========================================================
class SnapDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Snap.objects.all()

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return SnapUpdateSerializer
        elif self.request.method == 'DELETE':
            return SnapDeleteSerializer
        return SnapSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        # ここで SnapDeleteSerializer.delete() を呼ぶ
        serializer.delete(instance)
        return Response(
            {"message": f"Snap {instance.id} and related file deleted successfully."},
            status=status.HTTP_204_NO_CONTENT
        )
    
# =========================================================
# SnapCreate
# - post: スナップ新規作成
# - genericsのCreateAPIViewを継承して作成
# =========================================================
class SnapCreate(generics.CreateAPIView):
    #扱うクエリセットをSnapオブジェクト全てとして設定
    queryset = Snap.objects.all()

    #シリアライザーを設定
    serializer_class = SnapCreateSerializer

# =========================================================
# UserSignup
# - post: ユーザー新規登録
# =========================================================
class UserSignup(APIView): # APIViewを継承
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "ユーザー登録が完了しました"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# =========================================================
# UserInfoView
# - get: ログイン中ユーザー情報取得
# =========================================================
class UserInfoView(APIView):
    # ログイン中のユーザーのみアクセス可能
    permission_classes = [IsAuthenticated]

    # GET メソッドでユーザー情報を取得
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

# =========================================================
# FileUpload（削除予定）
# - post: ファイルアップロード
# =========================================================
class FileUpload(APIView):
    def post(self, request, *args, **kwargs):
        serializer = FileSerializer(data=request.data)
        if serializer.is_valid():
            file_obj = serializer.save()
            return Response(FileSerializer(file_obj).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
