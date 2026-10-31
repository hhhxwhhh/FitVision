from django.apps import AppConfig


class GrowthConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "growth"
    verbose_name = "成长与激励"

    def ready(self):
        import growth.signals  # noqa: F401
