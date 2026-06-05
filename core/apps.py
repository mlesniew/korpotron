import json
from pathlib import Path

from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "core"

    def ready(self) -> None:
        from django.contrib.auth.signals import user_logged_in

        user_logged_in.connect(seed_onboarding_defaults)


def seed_onboarding_defaults(
    sender: object, request: object, user: object, **kwargs: object
) -> None:
    from django.db import transaction

    from core.models import OnboardingState, Option, OptionGroup, Template

    fixture_path = Path(__file__).parent / "fixtures" / "onboarding_defaults.json"
    data = json.loads(fixture_path.read_text())

    with transaction.atomic():
        # Lock the user row so concurrent first-time logins are serialised.
        user.__class__.objects.select_for_update().get(pk=user.pk)

        if OnboardingState.objects.filter(user=user).exists():
            return

        if (
            Template.objects.filter(user=user).exists()
            or OptionGroup.objects.filter(user=user).exists()
        ):
            OnboardingState.objects.create(user=user)
            return

        for t in data["templates"]:
            Template.objects.create(
                user=user,
                name=t["name"],
                base_prompt=t["base_prompt"],
                generate_title=t["generate_title"],
            )
        for og in data["option_groups"]:
            group = OptionGroup.objects.create(user=user, name=og["name"])
            for opt in og["options"]:
                Option.objects.create(
                    group=group, name=opt["name"], instruction=opt["instruction"]
                )
        OnboardingState.objects.create(user=user)
