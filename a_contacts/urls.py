from django.urls import path

from a_contacts.views import contacts_list_view, csv_headers_htmx, csv_upload_view, dashboard_view, prompt_override_htmx, bulk_send_prompt_view, bulk_generate_email_dm_view, message_modal_view

app_name = 'a_contacts'

urlpatterns = [
    path('project/<int:project_pk>/upload/', csv_upload_view, name='upload'),
    path('project/<int:project_pk>/', contacts_list_view, name='list'),
    path('project/<int:project_pk>/headers/', csv_headers_htmx, name='headers_htmx'),
    path('project/<int:project_pk>/dashboard/', dashboard_view, name='dashboard'),
    path('project/<int:project_pk>/contact/<int:contact_pk>/step/<int:step_pk>/prompt/', prompt_override_htmx, name='prompt_override_htmx'),
    path('project/<int:project_pk>/contact/<int:contact_pk>/messages/', message_modal_view, name='message_modal'),
    path('project/<int:project_pk>/dashboard/bulk/send-prompt/', bulk_send_prompt_view, name='bulk_send_prompt'),
    path('project/<int:project_pk>/dashboard/bulk/generate-email-dm/', bulk_generate_email_dm_view, name='bulk_generate_email_dm'),
]