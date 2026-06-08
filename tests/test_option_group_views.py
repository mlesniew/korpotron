import pytest
from django.contrib.auth.models import User
from django.test import Client

from core.models import Option, OptionGroup


@pytest.fixture
def option_group(user: User) -> OptionGroup:
    group = OptionGroup.objects.create(user=user, name="Tone")
    Option.objects.create(group=group, name="Formal", instruction="Be formal.")
    return group


@pytest.fixture
def other_option_group(other_user: User) -> OptionGroup:
    group = OptionGroup.objects.create(user=other_user, name="Other Group")
    Option.objects.create(group=group, name="Option A", instruction="Do A.")
    return group


def formset_data(group_name: str, options: list[dict[str, str]]) -> dict[str, str]:
    data: dict[str, str] = {
        "name": group_name,
        "options-TOTAL_FORMS": str(len(options)),
        "options-INITIAL_FORMS": "0",
        "options-MIN_NUM_FORMS": "0",
        "options-MAX_NUM_FORMS": "1000",
    }
    for i, opt in enumerate(options):
        data[f"options-{i}-name"] = opt.get("name", "")
        data[f"options-{i}-instruction"] = opt.get("instruction", "")
        data[f"options-{i}-DELETE"] = opt.get("DELETE", "")
    return data


@pytest.mark.django_db
def test_option_group_list_requires_login(client: Client) -> None:
    response = client.get("/option-groups/")
    assert response.status_code == 302
    assert response["Location"].startswith("/accounts/login/")


@pytest.mark.django_db
def test_option_group_list_shows_only_own(
    client: Client,
    user: User,
    option_group: OptionGroup,
    other_option_group: OptionGroup,
) -> None:
    client.login(username="tester", password="pass1234")
    response = client.get("/option-groups/")
    assert response.status_code == 200
    assert option_group in response.context["object_list"]
    assert other_option_group not in response.context["object_list"]


@pytest.mark.django_db
def test_option_group_create(client: Client, user: User) -> None:
    client.login(username="tester", password="pass1234")
    response = client.post(
        "/option-groups/new/",
        formset_data("Style", [{"name": "Casual", "instruction": "Be casual."}]),
    )
    assert response.status_code == 302
    assert response["Location"] == "/option-groups/"
    group = OptionGroup.objects.get(user=user, name="Style")
    assert group.options.filter(name="Casual").exists()


@pytest.mark.django_db
def test_option_group_update(
    client: Client, user: User, option_group: OptionGroup
) -> None:
    option = option_group.options.first()
    assert option is not None
    client.login(username="tester", password="pass1234")
    data = {
        "name": "Tone Updated",
        "options-TOTAL_FORMS": "1",
        "options-INITIAL_FORMS": "1",
        "options-MIN_NUM_FORMS": "0",
        "options-MAX_NUM_FORMS": "1000",
        "options-0-id": str(option.pk),
        "options-0-name": "Formal",
        "options-0-instruction": "Be very formal.",
        "options-0-DELETE": "",
    }
    response = client.post(f"/option-groups/{option_group.pk}/edit/", data)
    assert response.status_code == 302
    assert response["Location"] == "/option-groups/"
    option_group.refresh_from_db()
    assert option_group.name == "Tone Updated"
    option.refresh_from_db()
    assert option.instruction == "Be very formal."


@pytest.mark.django_db
def test_option_group_delete(
    client: Client, user: User, option_group: OptionGroup
) -> None:
    pk = option_group.pk
    client.login(username="tester", password="pass1234")
    response = client.post(f"/option-groups/{pk}/delete/")
    assert response.status_code == 302
    assert response["Location"] == "/option-groups/"
    assert not OptionGroup.objects.filter(pk=pk).exists()
    assert not Option.objects.filter(group_id=pk).exists()


@pytest.mark.django_db
def test_option_group_update_other_user_returns_404(
    client: Client, user: User, other_option_group: OptionGroup
) -> None:
    client.login(username="tester", password="pass1234")
    response = client.post(
        f"/option-groups/{other_option_group.pk}/edit/",
        formset_data("Hacked", [{"name": "Bad", "instruction": "Evil."}]),
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_option_group_delete_other_user_returns_404(
    client: Client, user: User, other_option_group: OptionGroup
) -> None:
    client.login(username="tester", password="pass1234")
    response = client.post(f"/option-groups/{other_option_group.pk}/delete/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_option_group_create_requires_at_least_one_option(
    client: Client, user: User
) -> None:
    client.login(username="tester", password="pass1234")
    data = formset_data("Empty", [{"name": "X", "instruction": "Y", "DELETE": "on"}])
    response = client.post("/option-groups/new/", data)
    assert response.status_code == 200
    assert not OptionGroup.objects.filter(user=user, name="Empty").exists()


@pytest.mark.django_db
def test_option_group_create_rejects_duplicate_option_names(
    client: Client, user: User
) -> None:
    client.login(username="tester", password="pass1234")
    data = formset_data(
        "Dupe",
        [
            {"name": "Same", "instruction": "First."},
            {"name": "Same", "instruction": "Second."},
        ],
    )
    response = client.post("/option-groups/new/", data)
    assert response.status_code == 200
    assert not OptionGroup.objects.filter(user=user, name="Dupe").exists()


@pytest.mark.django_db
def test_option_group_update_delete_option(
    client: Client, user: User, option_group: OptionGroup
) -> None:
    """POSTing with one option's DELETE=on removes it from the DB; group and surviving option remain."""
    # Add a second option so deleting one doesn't trip the ≥1-option rule.
    surviving_option = Option.objects.create(
        group=option_group, name="Casual", instruction="Be casual."
    )
    deleted_option = option_group.options.exclude(pk=surviving_option.pk).first()
    assert deleted_option is not None

    client.login(username="tester", password="pass1234")
    data: dict[str, str] = {
        "name": option_group.name,
        "options-TOTAL_FORMS": "2",
        "options-INITIAL_FORMS": "2",
        "options-MIN_NUM_FORMS": "0",
        "options-MAX_NUM_FORMS": "1000",
        # First option (to be deleted)
        "options-0-id": str(deleted_option.pk),
        "options-0-name": deleted_option.name,
        "options-0-instruction": deleted_option.instruction,
        "options-0-DELETE": "on",
        # Second option (to survive)
        "options-1-id": str(surviving_option.pk),
        "options-1-name": surviving_option.name,
        "options-1-instruction": surviving_option.instruction,
        "options-1-DELETE": "",
    }
    response = client.post(f"/option-groups/{option_group.pk}/edit/", data)
    assert response.status_code == 302
    assert response["Location"] == "/option-groups/"
    assert not Option.objects.filter(pk=deleted_option.pk).exists()
    assert Option.objects.filter(pk=surviving_option.pk).exists()
    assert OptionGroup.objects.filter(pk=option_group.pk).exists()
