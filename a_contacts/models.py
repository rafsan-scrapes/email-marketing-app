from django.conf import settings
from django.db import models

from a_projects.models import Project
from a_sequences.models import SequenceStep


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


class ContactStepPrompt(models.Model):
    """
    Per-contact, per-step prompt override. When set, this replaces the template's
    default AIPromptConfig for AI field generation for this specific contact+step.
    """
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name='step_prompts'
    )
    sequence_step = models.ForeignKey(
        SequenceStep,
        on_delete=models.CASCADE,
        related_name='contact_prompts'
    )
    prompt_text = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        unique_together = ['contact', 'sequence_step']

    def __str__(self):
        return f"Prompt for {self.contact} - Step {self.sequence_step.order}"