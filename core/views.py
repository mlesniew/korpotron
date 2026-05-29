from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Count, QuerySet
from django.forms import BaseModelForm
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.forms import OptionFormSet
from core.models import OptionGroup, Template


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
