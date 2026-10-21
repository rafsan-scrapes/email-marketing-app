from django.conf import settings
from django.db import models

from a_projects.models import Project


class Contact(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='contacts'
    )
    data = models.JSONField(default=dict, blank=True)
    current_step = models.IntegerField(default=0)
    next_due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        key_val = self.data.get(self.project.key_column, '') if self.project.key_column else ''
        return f"{self.project.name} - {key_val}"