from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from a_projects.models import Project


def home_view(request):
    return render(request, 'a_home/home.html')


@login_required
def dashboard_view(request):
    projects = Project.objects.filter(owner=request.user)
    return render(request, 'a_home/dashboard.html', {'projects': projects})