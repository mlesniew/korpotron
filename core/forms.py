from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.forms import (
    BaseInlineFormSet,
    CharField,
    PasswordInput,
    ValidationError,
    inlineformset_factory,
)
from django.utils.crypto import constant_time_compare

from core.models import Option, OptionGroup


class OptionForm(forms.ModelForm):
    class Meta:
        model = Option
        fields = ["name", "instruction"]

    def clean_name(self) -> str:
        return self.cleaned_data["name"].strip()

    def clean_instruction(self) -> str:
        value = self.cleaned_data["instruction"].strip()
        if any(c in value for c in "\r\n"):
            raise ValidationError("Modifier instructions must be a single line.")
        return value


class RequiredOptionInlineFormSet(BaseInlineFormSet):
    def _construct_form(self, i: int, **kwargs: object) -> forms.BaseForm:
        form = super()._construct_form(i, **kwargs)
        form.empty_permitted = False
        return form

    def clean(self) -> None:
        super().clean()
        active_forms = [
            f for f in self.forms if f.cleaned_data and not f.cleaned_data.get("DELETE")
        ]
        if len(active_forms) < 1:
            raise ValidationError("At least one option is required.")
        names = [
            f.cleaned_data["name"] for f in active_forms if f.cleaned_data.get("name")
        ]
        if len(names) != len(set(names)):
            raise ValidationError("Option names must be unique within a group.")


OptionFormSet = inlineformset_factory(
    OptionGroup,
    Option,
    form=OptionForm,
    formset=RequiredOptionInlineFormSet,
    fields=["name", "instruction"],
    extra=0,
    can_delete=True,
)


class UserRegistrationForm(UserCreationForm):
    passphrase = CharField(widget=PasswordInput, label="Passphrase")

    def clean_passphrase(self) -> str:
        value = self.cleaned_data["passphrase"]
        if not constant_time_compare(value, settings.REGISTRATION_PASSPHRASE):
            raise ValidationError("Incorrect passphrase.")
        return value
