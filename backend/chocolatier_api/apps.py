from django.apps import AppConfig


class ChocolatierApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chocolatier_api'

    # アプリの準備ができたときに Django が 1 回だけ呼ぶ
    # - signals.py を読み込んで、削除のときの後片付け（実ファイル・使われていないタグ）を登録する（改修案件08）
    def ready(self):
        from . import signals  # noqa: F401（読み込むこと自体が目的）
