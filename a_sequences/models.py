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

    def get_default_template(self):
        """Get or create the default (condition-less) template for this step."""
        template, _ = self.templates.get_or_create(order=0, defaults={
            'subject': '',
            'body': '',
        })
        return template


class Template(models.Model):
    sequence_step = models.ForeignKey(
        SequenceStep,
        on_delete=models.CASCADE,
        related_name='templates'
    )
    order = models.IntegerField(default=0)
    subject = models.TextField(blank=True, default='')
    body = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']
        unique_together = ['sequence_step', 'order']

    def __str__(self):
        return f"{self.sequence_step} - Template {self.order}"

    @property
    def is_default(self):
        """Default template has order=0 and no conditions."""
        return self.order == 0 and not self.conditions.exists()

    def get_conditions_ordered(self):
        return self.conditions.order_by('order')


class TemplateCondition(models.Model):
    OPERATOR_EQUALS = 'equals'
    OPERATOR_NOT_EQUALS = 'not_equals'
    OPERATOR_CONTAINS = 'contains'
    OPERATOR_IS_EMPTY = 'is_empty'
    OPERATOR_IS_NOT_EMPTY = 'is_not_empty'
    OPERATOR_GREATER_THAN = 'greater_than'
    OPERATOR_LESS_THAN = 'less_than'

    OPERATOR_CHOICES = [
        (OPERATOR_EQUALS, 'equals'),
        (OPERATOR_NOT_EQUALS, 'not equals'),
        (OPERATOR_CONTAINS, 'contains'),
        (OPERATOR_IS_EMPTY, 'is empty'),
        (OPERATOR_IS_NOT_EMPTY, 'is not empty'),
        (OPERATOR_GREATER_THAN, 'greater than'),
        (OPERATOR_LESS_THAN, 'less than'),
    ]

    template = models.ForeignKey(
        Template,
        on_delete=models.CASCADE,
        related_name='conditions'
    )
    order = models.IntegerField(default=0)
    column_name = models.CharField(max_length=100)
    operator = models.CharField(max_length=20, choices=OPERATOR_CHOICES)
    value = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']
        unique_together = ['template', 'order']

    def __str__(self):
        return f"{self.template} - {self.column_name} {self.operator} {self.value}"

    @property
    def requires_value(self):
        return self.operator not in [self.OPERATOR_IS_EMPTY, self.OPERATOR_IS_NOT_EMPTY]