from django.conf import settings
from django.http import HttpRequest


def registration(request: HttpRequest) -> dict[str, bool]:
    return {"registration_enabled": bool(settings.REGISTRATION_PASSPHRASE)}
