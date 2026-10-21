from django.conf import settings
from django.db import models


class Project(models.Model):
    TYPE_EMAIL = 'email'
    TYPE_LINKEDIN_DM = 'linkedin_dm'
    TYPE_CHOICES = [
        (TYPE_EMAIL, 'Email'),
        (TYPE_LINKEDIN_DM, 'LinkedIn DM'),
    ]

    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    key_column = models.CharField(max_length=100, blank=True, null=True)
    csv_columns = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='projects'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Settings(models.Model):
    """Single-row settings model for app-wide configuration (Gemini API key)."""
    gemini_api_key = models.TextField(blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Settings'
        verbose_name_plural = 'Settings'

    def __str__(self):
        return 'Settings'

    def save(self, *args, **kwargs):
        # Enforce single row - always use pk=1
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        """Get or create the single settings instance."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj