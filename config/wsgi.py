import os

from django.core.wsgi import get_wsgi_application

# prod, not local (SPEC-006 결정 4): a deploy that forgets DJANGO_SETTINGS_MODULE
# fails on prod's required values instead of quietly running with DEBUG=True and
# console mail. manage.py keeps local for development; compose sets it explicitly.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

application = get_wsgi_application()
