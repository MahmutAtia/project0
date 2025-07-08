from django.apps import AppConfig


class PlansConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "plans"

    def ready(self):
        """
        Import signals when the app is ready.
        """
        import plans.signals
