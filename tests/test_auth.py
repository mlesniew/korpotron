import pytest
from django.contrib.auth.models import User
from django.test import Client


@pytest.mark.django_db
def test_valid_login_redirects_to_home(client: Client, user: User) -> None:
    response = client.post(
        "/accounts/login/",
        {"username": "tester", "password": "pass1234"},
        follow=True,
    )
    assert response.status_code == 200
    assert response.wsgi_request.path == "/"


@pytest.mark.django_db
def test_invalid_login_returns_form(client: Client, user: User) -> None:
    response = client.post(
        "/accounts/login/",
        {"username": "tester", "password": "wrongpassword"},
    )
    assert response.status_code == 200
    assert not response.wsgi_request.user.is_authenticated
    assert response.context["form"].errors


@pytest.mark.django_db
def test_logout_redirects_to_landing(client: Client, user: User) -> None:
    client.login(username="tester", password="pass1234")
    response = client.post("/accounts/logout/")
    assert response.status_code == 302
    assert response["Location"] == "/"


@pytest.mark.django_db
def test_inactive_user_cannot_login(client: Client) -> None:
    User.objects.create_user(username="inactive", password="pass1234", is_active=False)
    response = client.post(
        "/accounts/login/",
        {"username": "inactive", "password": "pass1234"},
    )
    assert response.status_code == 200
    assert not response.wsgi_request.user.is_authenticated
