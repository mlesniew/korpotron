from django.contrib import admin

from core.models import OnboardingState, Option, OptionGroup, Template


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "generate_title"]
    list_select_related = ["user"]


@admin.register(OptionGroup)
class OptionGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "user"]
    list_select_related = ["user"]


@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    list_display = ["name", "group"]
    list_select_related = ["group"]


@admin.register(OnboardingState)
class OnboardingStateAdmin(admin.ModelAdmin):
    list_display = ["user", "seeded_at"]
    list_select_related = ["user"]
