import json
import logging
import threading
from datetime import date, timedelta
from unittest.mock import patch

import httpx
import pytest
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.db import models as _models
from django.http import HttpResponse
from django.test import Client
from openai import APITimeoutError, OpenAIError

from core.llm import GenerateResult
from core.models import DailyGenerationCount, Option, OptionGroup, Template


@pytest.fixture
def template(user: User) -> Template:
    return Template.objects.create(
        user=user, name="Polite", base_prompt="Rewrite politely.", generate_title=False
    )


@pytest.fixture
def other_template(other_user: User) -> Template:
    return Template.objects.create(
        user=other_user, name="Other", base_prompt="Hi", generate_title=False
    )


@pytest.fixture
def group(user: User) -> OptionGroup:
    return OptionGroup.objects.create(user=user, name="Tone")


@pytest.fixture
def options(group: OptionGroup) -> list[Option]:
    return [
        Option.objects.create(group=group, name="Formal", instruction="Be formal."),
        Option.objects.create(group=group, name="Brief", instruction="Be brief."),
    ]


@pytest.fixture
def other_option(other_user: User) -> Option:
    og = OptionGroup.objects.create(user=other_user, name="Theirs")
    return Option.objects.create(group=og, name="X", instruction="x")


def _login(client: Client) -> None:
    client.login(username="tester", password="pass1234")


def _post(client: Client, **body: object) -> HttpResponse:
    return client.post(
        "/generate/", data=json.dumps(body), content_type="application/json"
    )


# --- GET / -----------------------------------------------------------------


@pytest.mark.django_db
def test_anonymous_home_shows_landing_page(client: Client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert b"Log in" in response.content
    assert b'id="generate-btn"' not in response.content


@pytest.mark.django_db
def test_authenticated_home_shows_generate_ui(
    client: Client, user: User, template: Template
) -> None:
    _login(client)
    response = client.get("/")
    assert response.status_code == 200
    assert b'id="generate-btn"' in response.content


@pytest.mark.django_db
def test_generate_page_lists_only_own(
    client: Client,
    user: User,
    template: Template,
    other_template: Template,
    group: OptionGroup,
) -> None:
    other_group = OptionGroup.objects.create(user=other_template.user, name="Theirs")
    _login(client)
    response = client.get("/")
    assert response.status_code == 200
    assert template in response.context["templates"]
    assert other_template not in response.context["templates"]
    assert group in response.context["option_groups"]
    assert other_group not in response.context["option_groups"]


# --- Page rendering (Phase 3) ---------------------------------------------


@pytest.mark.django_db
def test_generate_page_renders_form_and_options(
    client: Client, user: User, template: Template, options: list[Option]
) -> None:
    _login(client)
    html = client.get("/").content.decode()
    # template picker (pills) + input + generate button
    assert f'data-template-id="{template.pk}"' in html
    assert template.name in html
    assert 'id="input-text"' in html
    assert 'id="generate-btn"' in html
    # option group heading + buttons carrying their ids
    assert "Tone" in html
    assert f'data-option-id="{options[0].pk}"' in html
    assert f'data-option-id="{options[1].pk}"' in html


@pytest.mark.django_db
def test_generate_page_empty_state_when_no_templates(
    client: Client, user: User
) -> None:
    # Pre-create OnboardingState so the login signal skips seeding.
    # This represents a user who was onboarded but deleted all their templates.
    from core.models import OnboardingState

    OnboardingState.objects.create(user=user)
    _login(client)
    html = client.get("/").content.decode()
    # empty state links to template creation, no Generate button presented
    assert "/templates/new/" in html
    assert 'id="generate-btn"' not in html


# --- POST /generate/ -------------------------------------------------------


@pytest.mark.django_db
def test_generate_requires_login(client: Client, template: Template) -> None:
    response = _post(client, template_id=template.pk, text="hi")
    # login_required on a non-GET redirects to login
    assert response.status_code == 302


@pytest.mark.django_db
def test_generate_happy_path(
    client: Client, user: User, template: Template, options: list[Option]
) -> None:
    _login(client)
    with patch(
        "core.views.llm.generate",
        return_value=GenerateResult(title="", body="Rewritten politely."),
    ) as mock_generate:
        response = _post(
            client,
            template_id=template.pk,
            option_ids=[options[0].pk],
            text="rewrite me",
        )
    assert response.status_code == 200
    assert response.json() == {"title": "", "body": "Rewritten politely."}
    # the service was called with the resolved template + options + text
    called_template, called_options, called_text = mock_generate.call_args.args
    assert called_template == template
    assert [o.pk for o in called_options] == [options[0].pk]
    assert called_text == "rewrite me"


@pytest.mark.django_db
def test_generate_empty_text_rejected(client: Client, template: Template) -> None:
    _login(client)
    response = _post(client, template_id=template.pk, text="   ")
    assert response.status_code == 400
    assert "error" in response.json()


@pytest.mark.django_db
def test_generate_cross_user_template_rejected(
    client: Client, user: User, other_template: Template
) -> None:
    _login(client)
    response = _post(client, template_id=other_template.pk, text="hi")
    assert response.status_code == 400
    assert "error" in response.json()


@pytest.mark.django_db
def test_generate_cross_user_option_rejected(
    client: Client, user: User, template: Template, other_option: Option
) -> None:
    _login(client)
    response = _post(
        client, template_id=template.pk, option_ids=[other_option.pk], text="hi"
    )
    assert response.status_code == 400
    assert "error" in response.json()


@pytest.mark.django_db
def test_generate_two_options_same_group_rejected(
    client: Client, user: User, template: Template, options: list[Option]
) -> None:
    _login(client)
    response = _post(
        client,
        template_id=template.pk,
        option_ids=[options[0].pk, options[1].pk],
        text="hi",
    )
    assert response.status_code == 400
    assert "error" in response.json()


@pytest.mark.django_db
def test_generate_llm_error_maps_to_502_not_500(
    client: Client, user: User, template: Template, caplog: pytest.LogCaptureFixture
) -> None:
    _login(client)
    with caplog.at_level(logging.ERROR, logger="core.views"):
        with patch("core.views.llm.generate", side_effect=OpenAIError("boom")):
            response = _post(client, template_id=template.pk, text="secret input")
    assert response.status_code == 502
    body = response.json()
    assert "error" in body
    # the user's input is never echoed back
    assert "secret input" not in json.dumps(body)
    assert any(r.levelno == logging.ERROR for r in caplog.records)


@pytest.mark.django_db
def test_generate_timeout_maps_to_friendly_error(
    client: Client, user: User, template: Template
) -> None:
    _login(client)
    timeout = APITimeoutError(request=httpx.Request("POST", "http://x"))
    with patch("core.views.llm.generate", side_effect=timeout):
        response = _post(client, template_id=template.pk, text="hi")
    assert response.status_code == 502
    assert "error" in response.json()


@pytest.mark.django_db
def test_generate_creates_no_db_rows(
    client: Client, user: User, template: Template, options: list[Option]
) -> None:
    """R6 non-retention contract: the generate view must not persist user-supplied input text to any DB field. Extend this pattern to each new endpoint that accepts user text."""
    _login(client)

    def counts() -> tuple[int, int, int, int]:
        return (
            Template.objects.count(),
            OptionGroup.objects.count(),
            Option.objects.count(),
            Session.objects.count(),
        )

    before = counts()
    with patch(
        "core.views.llm.generate",
        return_value=GenerateResult(title="T", body="B"),
    ):
        response = _post(
            client,
            template_id=template.pk,
            option_ids=[options[0].pk],
            text="rewrite me",
        )
    assert response.status_code == 200
    assert counts() == before

    input_text = "rewrite me"

    for obj in [
        *Template.objects.all(),
        *OptionGroup.objects.all(),
        *Option.objects.all(),
    ]:
        for field in obj._meta.get_fields():
            if isinstance(field, (_models.CharField, _models.TextField)):
                assert input_text not in (getattr(obj, field.name) or "")


# --- Daily generation limit -----------------------------------------------


@pytest.fixture
def today() -> date:
    from django.utils import timezone

    return timezone.now().date()


@pytest.mark.django_db
def test_daily_limit_not_reached(
    client: Client, user: User, template: Template, settings: object, today: date
) -> None:
    settings.DAILY_GENERATION_LIMIT = 2  # type: ignore[attr-defined]
    DailyGenerationCount.objects.create(user=user, date=today, count=1)
    _login(client)
    with patch(
        "core.views.llm.generate",
        return_value=GenerateResult(title="", body="ok"),
    ):
        response = _post(client, template_id=template.pk, text="hi")
    assert response.status_code == 200
    assert DailyGenerationCount.objects.get(user=user, date=today).count == 2


@pytest.mark.django_db
def test_daily_limit_reached(
    client: Client, user: User, template: Template, settings: object, today: date
) -> None:
    settings.DAILY_GENERATION_LIMIT = 2  # type: ignore[attr-defined]
    DailyGenerationCount.objects.create(user=user, date=today, count=2)
    _login(client)
    with patch("core.views.llm.generate") as mock_generate:
        response = _post(client, template_id=template.pk, text="hi")
    assert response.status_code == 429
    assert "error" in response.json()
    mock_generate.assert_not_called()


@pytest.mark.django_db
def test_daily_limit_zero_means_unlimited(
    client: Client, user: User, template: Template, settings: object, today: date
) -> None:
    settings.DAILY_GENERATION_LIMIT = 0  # type: ignore[attr-defined]
    DailyGenerationCount.objects.create(user=user, date=today, count=999)
    _login(client)
    with patch(
        "core.views.llm.generate",
        return_value=GenerateResult(title="", body="ok"),
    ):
        response = _post(client, template_id=template.pk, text="hi")
    assert response.status_code == 200


@pytest.mark.django_db
def test_daily_limit_llm_error_does_not_increment(
    client: Client, user: User, template: Template, settings: object, today: date
) -> None:
    settings.DAILY_GENERATION_LIMIT = 5  # type: ignore[attr-defined]
    _login(client)
    with patch("core.views.llm.generate", side_effect=OpenAIError("boom")):
        response = _post(client, template_id=template.pk, text="hi")
    assert response.status_code == 502
    assert not DailyGenerationCount.objects.filter(user=user, date=today).exists()


@pytest.mark.django_db
def test_daily_limit_resets_next_day(
    client: Client, user: User, template: Template, settings: object, today: date
) -> None:
    settings.DAILY_GENERATION_LIMIT = 1  # type: ignore[attr-defined]
    yesterday = today - timedelta(days=1)
    DailyGenerationCount.objects.create(user=user, date=yesterday, count=1)
    _login(client)
    with patch(
        "core.views.llm.generate",
        return_value=GenerateResult(title="", body="ok"),
    ):
        response = _post(client, template_id=template.pk, text="hi")
    assert response.status_code == 200


@pytest.mark.django_db(transaction=True)
def test_rate_limit_concurrent_requests_at_boundary(
    user: User, template: Template, settings: object, today: date
) -> None:
    settings.DAILY_GENERATION_LIMIT = 2  # type: ignore[attr-defined]
    DailyGenerationCount.objects.create(user=user, date=today, count=1)

    # Authenticate both clients in the main thread to avoid concurrent session writes
    clients = [Client(), Client()]
    for c in clients:
        c.force_login(user)

    statuses: list[int] = []
    barrier = threading.Barrier(2)

    def make_request(c: Client) -> None:
        barrier.wait()
        resp = _post(c, template_id=template.pk, text="hi")
        statuses.append(resp.status_code)

    with patch(
        "core.views.llm.generate",
        return_value=GenerateResult(title="", body="ok"),
    ):
        threads = [threading.Thread(target=make_request, args=(c,)) for c in clients]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    assert sorted(statuses) == [200, 429]
    assert DailyGenerationCount.objects.get(user=user, date=today).count == 2


@pytest.mark.django_db(transaction=True)
def test_rate_limit_first_of_day_concurrent_requests(
    user: User, template: Template, settings: object, today: date
) -> None:
    settings.DAILY_GENERATION_LIMIT = 1  # type: ignore[attr-defined]

    # Authenticate both clients in the main thread to avoid concurrent session writes
    clients = [Client(), Client()]
    for c in clients:
        c.force_login(user)

    statuses: list[int] = []
    barrier = threading.Barrier(2)

    def make_request(c: Client) -> None:
        barrier.wait()
        resp = _post(c, template_id=template.pk, text="hi")
        statuses.append(resp.status_code)

    with patch(
        "core.views.llm.generate",
        return_value=GenerateResult(title="", body="ok"),
    ):
        threads = [threading.Thread(target=make_request, args=(c,)) for c in clients]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    assert sorted(statuses) == [200, 429]
    assert DailyGenerationCount.objects.get(user=user, date=today).count == 1
