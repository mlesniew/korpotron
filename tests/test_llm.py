from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import User

from core import llm
from core.models import Option, OptionGroup, Template


@pytest.fixture
def template(user: User) -> Template:
    return Template.objects.create(
        user=user, name="Polite", base_prompt="Rewrite politely.", generate_title=False
    )


@pytest.fixture
def title_template(user: User) -> Template:
    return Template.objects.create(
        user=user, name="Email", base_prompt="Write an email.", generate_title=True
    )


@pytest.fixture
def options(user: User) -> list[Option]:
    group = OptionGroup.objects.create(user=user, name="Tone")
    return [
        Option.objects.create(group=group, name="Formal", instruction="Be formal."),
        Option.objects.create(group=group, name="Brief", instruction="Be brief."),
    ]


@pytest.mark.django_db
def test_build_messages_system_has_app_prompt_and_tag_contract(
    template: Template,
) -> None:
    messages = llm.build_messages(template, [], "hi")
    system = messages[0]
    assert system["role"] == "system"
    assert "<body>" in system["content"]
    # title not requested -> no title contract
    assert "<title>" not in system["content"]


@pytest.mark.django_db
def test_build_messages_requests_title_when_generate_title(
    title_template: Template,
) -> None:
    messages = llm.build_messages(title_template, [], "hi")
    assert "<title>" in messages[0]["content"]


@pytest.mark.django_db
def test_build_messages_user_block_delimits_instructions_and_content(
    template: Template, options: list[Option]
) -> None:
    messages = llm.build_messages(template, options, "Hello there")
    user = messages[1]
    assert user["role"] == "user"
    content = user["content"]
    assert "<instructions>" in content and "</instructions>" in content
    assert "<content>" in content and "</content>" in content
    # base_prompt + each option instruction present, in order
    assert "Rewrite politely." in content
    assert "Be formal." in content
    assert "Be brief." in content
    assert content.index("Be formal.") < content.index("Be brief.")
    # the user text lands inside the content block
    assert "Hello there" in content


@pytest.mark.django_db
def test_build_messages_user_text_absent_from_system_message(
    template: Template,
) -> None:
    messages = llm.build_messages(template, [], "Hello there")
    assert "Hello there" not in messages[0]["content"]


def test_parse_result_title_and_body() -> None:
    raw = "<title>My Title</title>\n<body>The body text.</body>"
    result = llm.parse_result(raw)
    assert result.title == "My Title"
    assert result.body == "The body text."


def test_parse_result_body_only() -> None:
    raw = "<body>Just a body.</body>"
    result = llm.parse_result(raw)
    assert result.title == ""
    assert result.body == "Just a body."


def test_parse_result_no_body_tag_falls_back_to_raw() -> None:
    raw = "Some unstructured response with no tags."
    result = llm.parse_result(raw)
    assert result.title == ""
    assert result.body == "Some unstructured response with no tags."


@pytest.mark.django_db
def test_generate_calls_create_with_model_and_messages(template: Template) -> None:
    fake_message = MagicMock()
    fake_message.content = "<body>Rewritten.</body>"
    fake_completion = MagicMock()
    fake_completion.choices = [MagicMock(message=fake_message)]

    fake_client = MagicMock()
    fake_client.chat.completions.create.return_value = fake_completion

    with patch.object(llm, "_get_client", return_value=fake_client):
        result = llm.generate(template, [], "input text")

    assert result.body == "Rewritten."
    call = fake_client.chat.completions.create.call_args
    assert call.kwargs["model"]  # configured model passed through
    messages = call.kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert "input text" in messages[1]["content"]
