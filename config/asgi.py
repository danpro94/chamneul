import os

from django.core.asgi import get_asgi_application

# prod by default, like wsgi.py (SPEC-006 결정 4).
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

application = get_asgi_application()
