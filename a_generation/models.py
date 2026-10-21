from django.conf import settings
from django.db import models

from a_contacts.models import Contact
from a_sequences.models import Template


class GeneratedAIField(models.Model):
    STATUS_SUCCESS = 'success'
    STATUS_ERROR = 'error'
    STATUS_CHOICES = [
        (STATUS_SUCCESS, 'Success'),
        (STATUS_ERROR, 'Error'),
    ]

    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name='generated_ai_fields'
    )
    template = models.ForeignKey(
        Template,
        on_delete=models.CASCADE,
        related_name='generated_ai_fields'
    )
    placeholder_name = models.CharField(max_length=100)
    value = models.TextField(blank=True, default='')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_SUCCESS)
    error_message = models.TextField(blank=True, default='')
    generated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-generated_at']
        unique_together = ['contact', 'template', 'placeholder_name']

    def __str__(self):
        return f"{self.contact} - {self.template} - {self.placeholder_name} ({self.status})"