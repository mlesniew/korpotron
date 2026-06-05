from django.forms import (
    BaseInlineFormSet,
    ValidationError,
    inlineformset_factory,
)

from core.models import Option, OptionGroup


class RequiredOptionInlineFormSet(BaseInlineFormSet):
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
    formset=RequiredOptionInlineFormSet,
    fields=["name", "instruction"],
    extra=1,
    can_delete=True,
)
