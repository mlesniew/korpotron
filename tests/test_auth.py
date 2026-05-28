import pytest
from django.contrib.auth.models import User
from django.test import Client


@pytest.fixture
def user(db: None) -> User:
    return User.objects.create_user(username="tester", password="pass1234")


@pytest.mark.django_db
def test_unauthenticated_redirects_to_login(client: Client) -> None:
    response = client.get("/")
    assert response.status_code == 302
    assert response["Location"].startswith("/accounts/login/")


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
def test_logout_redirects_to_login(client: Client, user: User) -> None:
    client.login(username="tester", password="pass1234")
    response = client.post("/accounts/logout/")
    assert response.status_code == 302
    assert response["Location"].startswith("/accounts/login/")
