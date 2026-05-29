import pytest
from django.contrib.auth.models import User
from django.test import Client

from core.models import Template


@pytest.fixture
def other_user(db: None) -> User:
    return User.objects.create_user(username="other", password="pass1234")


@pytest.fixture
def template(user: User) -> Template:
    return Template.objects.create(user=user, name="My Template", base_prompt="Hello")


@pytest.fixture
def other_template(other_user: User) -> Template:
    return Template.objects.create(user=other_user, name="Other Template", base_prompt="Hi")


@pytest.mark.django_db
def test_template_list_requires_login(client: Client) -> None:
    response = client.get("/templates/")
    assert response.status_code == 302
    assert response["Location"].startswith("/accounts/login/")


@pytest.mark.django_db
def test_template_list_shows_only_own(
    client: Client, user: User, template: Template, other_template: Template
) -> None:
    client.login(username="tester", password="pass1234")
    response = client.get("/templates/")
    assert response.status_code == 200
    assert template in response.context["object_list"]
    assert other_template not in response.context["object_list"]


@pytest.mark.django_db
def test_template_create(client: Client, user: User) -> None:
    client.login(username="tester", password="pass1234")
    response = client.post(
        "/templates/new/",
        {"name": "New Template", "base_prompt": "Prompt text", "generate_title": False},
    )
    assert response.status_code == 302
    assert response["Location"] == "/templates/"
    assert Template.objects.filter(user=user, name="New Template").exists()


@pytest.mark.django_db
def test_template_update(client: Client, user: User, template: Template) -> None:
    client.login(username="tester", password="pass1234")
    response = client.post(
        f"/templates/{template.pk}/edit/",
        {"name": "Updated Name", "base_prompt": "New prompt", "generate_title": False},
    )
    assert response.status_code == 302
    assert response["Location"] == "/templates/"
    template.refresh_from_db()
    assert template.name == "Updated Name"


@pytest.mark.django_db
def test_template_delete(client: Client, user: User, template: Template) -> None:
    client.login(username="tester", password="pass1234")
    response = client.post(f"/templates/{template.pk}/delete/")
    assert response.status_code == 302
    assert response["Location"] == "/templates/"
    assert not Template.objects.filter(pk=template.pk).exists()


@pytest.mark.django_db
def test_template_update_other_user_returns_404(
    client: Client, user: User, other_template: Template
) -> None:
    client.login(username="tester", password="pass1234")
    response = client.post(
        f"/templates/{other_template.pk}/edit/",
        {"name": "Hacked", "base_prompt": "Bad", "generate_title": False},
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_template_delete_other_user_returns_404(
    client: Client, user: User, other_template: Template
) -> None:
    client.login(username="tester", password="pass1234")
    response = client.post(f"/templates/{other_template.pk}/delete/")
    assert response.status_code == 404
