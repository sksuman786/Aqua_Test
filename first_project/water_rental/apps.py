from django.apps import AppConfig


class AquaguardConfig(AppConfig):
    name = 'water_rental'

    def ready(self):
        import water_rental.signals


