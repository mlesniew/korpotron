from django.conf import settings
from django.db import models


class Template(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="templates",
    )
    name = models.CharField(max_length=200)
    base_prompt = models.TextField()
    generate_title = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class OptionGroup(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="option_groups",
    )
    name = models.CharField(max_length=200)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Option(models.Model):
    group = models.ForeignKey(
        OptionGroup,
        on_delete=models.CASCADE,
        related_name="options",
    )
    name = models.CharField(max_length=200)
    instruction = models.TextField()

    def __str__(self) -> str:
        return self.name
