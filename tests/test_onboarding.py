import pytest
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in

from core.models import OnboardingState, OptionGroup, Template


def _fire_login_signal(user: User) -> None:
    user_logged_in.send(sender=user.__class__, request=None, user=user)


@pytest.mark.django_db
def test_first_login_seeds_defaults(user: User) -> None:
    _fire_login_signal(user)

    assert Template.objects.filter(user=user).count() == 3
    assert OptionGroup.objects.filter(user=user).count() == 3
    assert OnboardingState.objects.filter(user=user).exists() is True


@pytest.mark.django_db
def test_second_login_does_not_reseed(user: User) -> None:
    _fire_login_signal(user)
    _fire_login_signal(user)

    assert Template.objects.filter(user=user).count() == 3
    assert OptionGroup.objects.filter(user=user).count() == 3
    assert OnboardingState.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_user_with_existing_content_is_not_seeded(user: User) -> None:
    Template.objects.create(
        user=user,
        name="My Template",
        base_prompt="hello",
        generate_title=False,
    )
    _fire_login_signal(user)

    assert Template.objects.filter(user=user).count() == 1
    assert OnboardingState.objects.filter(user=user).exists() is False


@pytest.mark.django_db
def test_deleting_defaults_then_logging_in_does_not_reseed(user: User) -> None:
    _fire_login_signal(user)

    Template.objects.filter(user=user).delete()
    OptionGroup.objects.filter(user=user).delete()

    _fire_login_signal(user)

    assert Template.objects.filter(user=user).count() == 0
    assert OptionGroup.objects.filter(user=user).count() == 0
