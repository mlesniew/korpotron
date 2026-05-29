from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import QuerySet
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.models import Template


class TemplateListView(LoginRequiredMixin, ListView):
    model = Template

    def get_queryset(self) -> QuerySet[Template]:
        return Template.objects.filter(user=self.request.user)


class TemplateCreateView(LoginRequiredMixin, CreateView):
    model = Template
    fields = ["name", "base_prompt", "generate_title"]
    success_url = reverse_lazy("template-list")

    def form_valid(self, form):  # type: ignore[override]
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
