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
        unique_together = [("user", "name")]

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

    class Meta:
        unique_together = [("group", "name")]

    def __str__(self) -> str:
        return self.name


class DailyGenerationCount(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="daily_generation_counts",
    )
    date = models.DateField()
    count = models.IntegerField(default=0)

    class Meta:
        unique_together = [("user", "date")]
