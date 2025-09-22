from django.urls import path
from .views import (
    SnapList,
    SnapCreate,
    SnapDetail,
    UserSignup,
    UserInfoView,
    FileUpload,
)

urlpatterns = [
       path('snap/', SnapList.as_view(), name='snap-list'),
       path('snap/create/', SnapCreate.as_view(), name='snap-create'),
       path('snap/<int:pk>/',SnapDetail.as_view(), name='snap-detail'),
       path('signup/', UserSignup.as_view(), name='user-signup'),
       path('user-info/', UserInfoView.as_view(), name='user_info'),
       path("files/upload/", FileUpload.as_view(), name="file-upload"),
]