from django.conf import settings
from django.core.exceptions import ValidationError
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

    def clean(self) -> None:
        self.base_prompt = self.base_prompt.strip()


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

    def clean(self) -> None:
        self.instruction = self.instruction.strip()
        if "\n" in self.instruction:
            raise ValidationError(
                {"instruction": "Modifier instructions must be a single line."}
            )


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

    def __str__(self) -> str:
        return f"{self.user} / {self.date} ({self.count})"


class OnboardingState(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="onboarding_state",
    )
    seeded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return str(self.user)
