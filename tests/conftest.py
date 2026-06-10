import pytest
from django.contrib.auth.models import User


@pytest.fixture(autouse=True)
def use_simple_static_storage(settings: pytest.FixtureRequest) -> None:
    # CompressedManifestStaticFilesStorage requires a collectstatic manifest;
    # swap to the plain backend so tests don't need a pre-built staticfiles dir.
    settings.STORAGES = {  # type: ignore[attr-defined]
        **settings.STORAGES,  # type: ignore[attr-defined]
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    }


@pytest.fixture
def user(db: None) -> User:
    return User.objects.create_user(username="tester", password="pass1234")


@pytest.fixture
def other_user(db: None) -> User:
    return User.objects.create_user(username="other", password="pass1234")
