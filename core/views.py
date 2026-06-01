import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Count, QuerySet
from django.forms import BaseModelForm
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    TemplateView,
    UpdateView,
)
from openai import OpenAIError

from core import llm
from core.forms import OptionFormSet
from core.models import Option, OptionGroup, Template


class TemplateListView(LoginRequiredMixin, ListView):
    model = Template

    def get_queryset(self) -> QuerySet[Template]:
        return Template.objects.filter(user=self.request.user)


class TemplateCreateView(LoginRequiredMixin, CreateView):
    model = Template
    fields = ["name", "base_prompt", "generate_title"]
    success_url = reverse_lazy("template-list")

    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        form.instance.user = self.request.user
        return super().form_valid(form)


class TemplateUpdateView(LoginRequiredMixin, UpdateView):
    model = Template
    fields = ["name", "base_prompt", "generate_title"]
    success_url = reverse_lazy("template-list")

    def get_queryset(self) -> QuerySet[Template]:
        return Template.objects.filter(user=self.request.user)


class TemplateDeleteView(LoginRequiredMixin, DeleteView):
    model = Template
    success_url = reverse_lazy("template-list")

    def get_queryset(self) -> QuerySet[Template]:
        return Template.objects.filter(user=self.request.user)


class OptionGroupListView(LoginRequiredMixin, ListView):
    model = OptionGroup

    def get_queryset(self) -> QuerySet[OptionGroup]:
        return OptionGroup.objects.filter(user=self.request.user).annotate(
            options_count=Count("options")
        )


class OptionGroupCreateView(LoginRequiredMixin, CreateView):
    model = OptionGroup
    fields = ["name"]
    success_url = reverse_lazy("option-group-list")

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        context = super().get_context_data(**kwargs)
        if not hasattr(self, "_formset"):
            self._formset: OptionFormSet = OptionFormSet(self.request.POST or None)
        context["formset"] = self._formset
        return context

    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        form.instance.user = self.request.user
        self._formset = OptionFormSet(self.request.POST, instance=form.instance)
        if self._formset.is_valid():
            with transaction.atomic():
                self.object = form.save()
                self._formset.instance = self.object
                self._formset.save()
            return HttpResponseRedirect(self.get_success_url())
        self.object = None
        return self.render_to_response(self.get_context_data(form=form))


class OptionGroupUpdateView(LoginRequiredMixin, UpdateView):
    model = OptionGroup
    fields = ["name"]
    success_url = reverse_lazy("option-group-list")

    def get_queryset(self) -> QuerySet[OptionGroup]:
        return OptionGroup.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        context = super().get_context_data(**kwargs)
        if not hasattr(self, "_formset"):
            self._formset: OptionFormSet = OptionFormSet(
                self.request.POST or None, instance=self.object
            )
        context["formset"] = self._formset
        return context

    def form_valid(self, form: BaseModelForm) -> HttpResponse:
        self._formset = OptionFormSet(self.request.POST, instance=self.object)
        if self._formset.is_valid():
            with transaction.atomic():
                form.save()
                self._formset.save()
            return HttpResponseRedirect(self.get_success_url())
        return self.render_to_response(self.get_context_data(form=form))


class OptionGroupDeleteView(LoginRequiredMixin, DeleteView):
    model = OptionGroup
    success_url = reverse_lazy("option-group-list")

    def get_queryset(self) -> QuerySet[OptionGroup]:
        return OptionGroup.objects.filter(user=self.request.user)


class GenerateView(LoginRequiredMixin, TemplateView):
    """The north-star flow at `/`: pick a template, toggle options, generate."""

    template_name = "core/generate.html"

    def get_context_data(self, **kwargs: object) -> dict[str, object]:
        context = super().get_context_data(**kwargs)
        context["templates"] = Template.objects.filter(user=self.request.user)
        context["option_groups"] = OptionGroup.objects.filter(
            user=self.request.user
        ).prefetch_related("options")
        return context


@login_required
@require_POST
def generate_api(request: HttpRequest) -> JsonResponse:
    """Validate ownership + the one-per-group invariant, call the LLM, return JSON.

    Never persists or logs the input/output (hard non-retention NFR). On LLM /
    transport failure, returns a friendly error with a non-500 status so the
    frontend can show an inline alert — no stack trace or input is echoed.
    """
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid request."}, status=400)

    if not isinstance(payload, dict):
        return JsonResponse({"error": "Invalid request."}, status=400)

    text = payload.get("text")
    if not isinstance(text, str) or not text.strip():
        return JsonResponse(
            {"error": "Please enter some text to transform."}, status=400
        )

    try:
        template_id = int(payload.get("template_id"))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return JsonResponse({"error": "Please choose a template."}, status=400)

    template = Template.objects.filter(user=request.user, pk=template_id).first()
    if template is None:
        return JsonResponse({"error": "Template not found."}, status=400)

    raw_option_ids = payload.get("option_ids", [])
    if not isinstance(raw_option_ids, list):
        return JsonResponse({"error": "Invalid options."}, status=400)
    try:
        option_ids = {int(oid) for oid in raw_option_ids}
    except (TypeError, ValueError):
        return JsonResponse({"error": "Invalid options."}, status=400)

    options = list(
        Option.objects.filter(
            group__user=request.user, pk__in=option_ids
        ).select_related("group")
    )
    if len(options) != len(option_ids):
        return JsonResponse(
            {"error": "One or more options were not found."}, status=400
        )

    group_ids = [option.group.pk for option in options]
    if len(group_ids) != len(set(group_ids)):
        return JsonResponse(
            {"error": "Only one option per group may be selected."}, status=400
        )

    try:
        result = llm.generate(template, options, text)
    except OpenAIError:
        # Do not log or echo the input/prompt/output (non-retention NFR).
        return JsonResponse(
            {"error": "Text generation failed. Please try again."}, status=502
        )

    return JsonResponse({"title": result.title, "body": result.body})
