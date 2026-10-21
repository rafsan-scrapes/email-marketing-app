from django.urls import path

from a_sequences.views import sequence_configure_view

app_name = 'a_sequences'

urlpatterns = [
    path('project/<int:project_pk>/configure/', sequence_configure_view, name='configure'),
]