# =========================================================
# signals.py（改修案件08）
# - 「DB の行が消えたら、後片付けをする」処理をまとめたファイル
# - シグナル：モデルの保存・削除などのタイミングで、Django が自動で呼んでくれる関数
#   → API から消しても、管理画面から消しても、利用者ごと消しても、同じ後片付けが必ず動く
#   （以前は API の削除の中にしか後片付けがなく、管理画面で消すと実ファイルが残っていた）
# - apps.py の ready() でこのファイルを読み込むと、シグナルが登録される
# =========================================================
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import File, Snap
from .services.files import remove_physical_file
from .services.tags import delete_unused_tags


# =========================================================
# スナップが消えたとき
# - ① 画像（File の行）も消す
#      スナップと画像は 1 対 1（業務の原則）なので、スナップが消えたら画像も要らない
#      File の行が消えると、下の file_deleted で実ファイルも消える
# - ② どのスナップにも付いていないタグを消す
# - 利用者を消したときも、その人のスナップが CASCADE で消えるので、ここが 1 件ずつ呼ばれる
# =========================================================
@receiver(post_delete, sender=Snap)
def snap_deleted(sender, instance, **kwargs):
    # ① file_id：Snap の行に入っている File の ID（instance.file を読むと、消えた File を取りに行ってしまうため ID を使う）
    File.objects.filter(id=instance.file_id).delete()

    # ②
    delete_unused_tags()


# =========================================================
# File（画像の行）が消えたとき
# - 実ファイルを消す（すでに無ければ何もしない）
# - 管理画面で File を消したときは、CASCADE でそのスナップも消える
# =========================================================
@receiver(post_delete, sender=File)
def file_deleted(sender, instance, **kwargs):
    remove_physical_file(instance.path)
