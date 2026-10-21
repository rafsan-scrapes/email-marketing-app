from django.urls import path

from a_projects.views import (
    ProjectCreateView,
    ProjectDeleteView,
    ProjectListView,
    project_create_htmx,
    project_delete_confirm_htmx,
    settings_view,
)

app_name = 'a_projects'

urlpatterns = [
    path('', ProjectListView.as_view(), name='list'),
    path('create/', ProjectCreateView.as_view(), name='create'),
    path('<int:pk>/delete/', ProjectDeleteView.as_view(), name='delete'),
    path('settings/', settings_view, name='settings'),
    # HTMX endpoints
    path('create/htmx/', project_create_htmx, name='create_htmx'),
    path('<int:pk>/delete/htmx/', project_delete_confirm_htmx, name='delete_confirm_htmx'),
]