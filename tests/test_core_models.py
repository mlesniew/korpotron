import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from core.models import Option, OptionGroup, Template


@pytest.mark.django_db
def test_template_creation(user: User) -> None:
    t = Template.objects.create(user=user, name="My Template", base_prompt="Say hello.")
    assert t.name == "My Template"
    assert t.base_prompt == "Say hello."
    assert t.generate_title is False
    assert str(t) == t.name


@pytest.mark.django_db
def test_option_group_creation(user: User) -> None:
    og = OptionGroup.objects.create(user=user, name="Tone")
    assert og.name == "Tone"
    assert og.user == user
    assert str(og) == og.name


@pytest.mark.django_db
def test_option_creation(user: User) -> None:
    og = OptionGroup.objects.create(user=user, name="Tone")
    o = Option.objects.create(
        group=og, name="Formal", instruction="Use formal language."
    )
    assert o.name == "Formal"
    assert o.instruction == "Use formal language."
    assert o.group == og
    assert str(o) == o.name


@pytest.mark.django_db
def test_user_delete_cascades_templates(user: User) -> None:
    Template.objects.create(user=user, name="T", base_prompt="x")
    user.delete()
    assert Template.objects.count() == 0


@pytest.mark.django_db
def test_user_delete_cascades_option_groups(user: User) -> None:
    OptionGroup.objects.create(user=user, name="G")
    user.delete()
    assert OptionGroup.objects.count() == 0


@pytest.mark.django_db
def test_option_group_delete_cascades_options(user: User) -> None:
    og = OptionGroup.objects.create(user=user, name="G")
    Option.objects.create(group=og, name="O", instruction="x")
    og.delete()
    assert Option.objects.count() == 0


@pytest.mark.django_db
def test_option_clean_strips_instruction(user: User) -> None:
    og = OptionGroup.objects.create(user=user, name="G")
    o = Option(group=og, name="O", instruction="  Be brief.  ")
    o.clean()
    assert o.instruction == "Be brief."


@pytest.mark.django_db
def test_option_clean_raises_on_newline(user: User) -> None:
    og = OptionGroup.objects.create(user=user, name="G")
    o = Option(group=og, name="O", instruction="Line one.\nLine two.")
    with pytest.raises(ValidationError) as exc_info:
        o.clean()
    assert "instruction" in exc_info.value.message_dict


@pytest.mark.django_db
def test_template_clean_strips_base_prompt(user: User) -> None:
    t = Template(user=user, name="T", base_prompt="  Hello.  ")
    t.clean()
    assert t.base_prompt == "Hello."
