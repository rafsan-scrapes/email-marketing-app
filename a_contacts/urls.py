from django.urls import path

from a_contacts.views import csv_upload_view

app_name = 'a_contacts'

urlpatterns = [
    path('project/<int:project_pk>/upload/', csv_upload_view, name='upload'),
]