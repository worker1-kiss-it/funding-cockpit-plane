from django.apps import AppConfig


class FundingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "plane.funding"
    verbose_name = "Funding Cockpit"

    def ready(self):
        import plane.funding.signals  # noqa: F401
