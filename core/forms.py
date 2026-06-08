from django.forms import (
    BaseInlineFormSet,
    ValidationError,
    inlineformset_factory,
)

from core.models import Option, OptionGroup


class RequiredOptionInlineFormSet(BaseInlineFormSet):
    def _construct_form(self, i: int, **kwargs: object) -> object:
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
    formset=RequiredOptionInlineFormSet,
    fields=["name", "instruction"],
    extra=0,
    can_delete=True,
)
