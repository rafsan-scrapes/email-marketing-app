from django.conf import settings
from django.db import models

from a_projects.models import Project


class SequenceStep(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='sequence_steps'
    )
    name = models.CharField(max_length=255)
    order = models.IntegerField(default=0)
    default_due_offset_days = models.IntegerField(default=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']
        unique_together = ['project', 'order']

    def __str__(self):
        return f"{self.project.name} - Step {self.order}: {self.name}"