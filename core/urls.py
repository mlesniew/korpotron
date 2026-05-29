from django.urls import path

from core.views import (
    TemplateCreateView,
    TemplateDeleteView,
    TemplateListView,
    TemplateUpdateView,
)

urlpatterns = [
    path("", TemplateListView.as_view(), name="template-list"),
    path("new/", TemplateCreateView.as_view(), name="template-create"),
    path("<int:pk>/edit/", TemplateUpdateView.as_view(), name="template-update"),
    path("<int:pk>/delete/", TemplateDeleteView.as_view(), name="template-delete"),
]
