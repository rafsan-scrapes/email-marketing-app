from django.urls import path

from a_sequences.views import sequence_configure_view, template_configure_view, ai_prompt_configure_view

app_name = 'a_sequences'

urlpatterns = [
    path('project/<int:project_pk>/configure/', sequence_configure_view, name='configure'),
    path('project/<int:project_pk>/step/<int:step_pk>/templates/', template_configure_view, name='template_configure'),
    path('project/<int:project_pk>/step/<int:step_pk>/template/<int:template_pk>/ai/', ai_prompt_configure_view, name='ai_prompt_configure'),
]