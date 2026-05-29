from django.urls import path

from core.views import (
    OptionGroupCreateView,
    OptionGroupDeleteView,
    OptionGroupListView,
    OptionGroupUpdateView,
)

urlpatterns = [
    path("", OptionGroupListView.as_view(), name="option-group-list"),
    path("new/", OptionGroupCreateView.as_view(), name="option-group-create"),
    path("<int:pk>/edit/", OptionGroupUpdateView.as_view(), name="option-group-update"),
    path("<int:pk>/delete/", OptionGroupDeleteView.as_view(), name="option-group-delete"),
]
