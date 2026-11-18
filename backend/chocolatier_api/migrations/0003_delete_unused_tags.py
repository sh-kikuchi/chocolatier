# =========================================================
# 0003：どのスナップにも付いていないタグを 1 回だけ片付ける（改修案件08）
# - これ以降は、タグを付け替えたとき・スナップを消したときに自動で消える（services/tags.py）
# - それより前に残っていたタグを、ここでまとめて消す
# - DB の構造は変えない（データだけを片付けるマイグレーション）
# =========================================================
from django.db import migrations


def delete_unused_tags(apps, schema_editor):
    # マイグレーションの中では、models.py を直接 import せず apps.get_model で取る（その時点の形のモデルを使うため）
    Tag = apps.get_model('chocolatier_api', 'Tag')
    Tag.objects.filter(snaps__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('chocolatier_api', '0002_tag_snap_tags'),
    ]

    operations = [
        # 戻すとき（migrate で 0002 に戻す）は何もしない（消したタグは戻せない）
        migrations.RunPython(delete_unused_tags, migrations.RunPython.noop),
    ]
