import pytest
from django.contrib.auth.models import User
from django.test import Client


@pytest.mark.django_db
def test_register_get_blocked_when_passphrase_unset(
    client: Client, settings: object
) -> None:
    settings.REGISTRATION_PASSPHRASE = ""
    response = client.get("/register/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_register_post_blocked_when_passphrase_unset(
    client: Client, settings: object
) -> None:
    settings.REGISTRATION_PASSPHRASE = ""
    response = client.post(
        "/register/",
        {
            "username": "newuser",
            "password1": "S3cur3Pass!",
            "password2": "S3cur3Pass!",
            "passphrase": "secret",
        },
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_register_get_returns_200(client: Client, settings: object) -> None:
    settings.REGISTRATION_PASSPHRASE = "secret"
    response = client.get("/register/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_register_wrong_passphrase_rejected(client: Client, settings: object) -> None:
    settings.REGISTRATION_PASSPHRASE = "secret"
    response = client.post(
        "/register/",
        {
            "username": "newuser",
            "password1": "S3cur3Pass!",
            "password2": "S3cur3Pass!",
            "passphrase": "wrong",
        },
    )
    assert response.status_code == 200
    assert not User.objects.filter(username="newuser").exists()


@pytest.mark.django_db
def test_register_valid_creates_user_and_redirects(
    client: Client, settings: object
) -> None:
    settings.REGISTRATION_PASSPHRASE = "secret"
    response = client.post(
        "/register/",
        {
            "username": "newuser",
            "password1": "S3cur3Pass!",
            "password2": "S3cur3Pass!",
            "passphrase": "secret",
        },
    )
    assert response.status_code == 302
    assert response["Location"] == "/accounts/login/"
    user = User.objects.filter(username="newuser").first()
    assert user is not None
    assert user.is_active
