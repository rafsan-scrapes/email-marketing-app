from django.urls import path

from a_contacts.views import contacts_list_view, csv_headers_htmx, csv_upload_view

app_name = 'a_contacts'

urlpatterns = [
    path('project/<int:project_pk>/upload/', csv_upload_view, name='upload'),
    path('project/<int:project_pk>/', contacts_list_view, name='list'),
    path('project/<int:project_pk>/headers/', csv_headers_htmx, name='headers_htmx'),
]