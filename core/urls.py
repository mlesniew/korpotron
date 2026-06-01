from django.urls import path

from core.views import (
    GenerateView,
    OptionGroupCreateView,
    OptionGroupDeleteView,
    OptionGroupListView,
    OptionGroupUpdateView,
    TemplateCreateView,
    TemplateDeleteView,
    TemplateListView,
    TemplateUpdateView,
    generate_api,
)

urlpatterns = [
    path("", GenerateView.as_view(), name="home"),
    path("generate/", generate_api, name="generate-api"),
    path("templates/", TemplateListView.as_view(), name="template-list"),
    path("templates/new/", TemplateCreateView.as_view(), name="template-create"),
    path(
        "templates/<int:pk>/edit/", TemplateUpdateView.as_view(), name="template-update"
    ),
    path(
        "templates/<int:pk>/delete/",
        TemplateDeleteView.as_view(),
        name="template-delete",
    ),
    path("option-groups/", OptionGroupListView.as_view(), name="option-group-list"),
    path(
        "option-groups/new/",
        OptionGroupCreateView.as_view(),
        name="option-group-create",
    ),
    path(
        "option-groups/<int:pk>/edit/",
        OptionGroupUpdateView.as_view(),
        name="option-group-update",
    ),
    path(
        "option-groups/<int:pk>/delete/",
        OptionGroupDeleteView.as_view(),
        name="option-group-delete",
    ),
]
