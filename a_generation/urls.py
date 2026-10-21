from django.urls import path

from a_generation.views import generate_ai_fields_view, generate_email_dm_view

app_name = 'a_generation'

urlpatterns = [
    path(
        'project/<int:project_pk>/contact/<int:contact_pk>/step/<int:step_pk>/ai-fields/',
        generate_ai_fields_view,
        name='generate_ai_fields'
    ),
    path(
        'project/<int:project_pk>/contact/<int:contact_pk>/step/<int:step_pk>/email-dm/',
        generate_email_dm_view,
        name='generate_email_dm'
    ),
]