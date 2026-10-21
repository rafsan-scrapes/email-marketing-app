from django.urls import path
from a_home.views import home_view, dashboard_view

app_name = 'a_home'

urlpatterns = [
    path('', home_view, name='home'),
    path('dashboard/', dashboard_view, name='dashboard'),
]