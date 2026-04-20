from django.apps import AppConfig


class BankingSystemConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "banking_system"

    def ready(self):
    # Import signals when the app is ready
        import banking_system.signals