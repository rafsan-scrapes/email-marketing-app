from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView

from a_projects.models import Project


class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = 'a_projects/list.html'
    context_object_name = 'projects'

    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user)


class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    template_name = 'a_projects/create.html'
    fields = ['name', 'type']

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('a_projects:list')


class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    model = Project
    template_name = 'a_projects/delete_confirm.html'
    context_object_name = 'project'

    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user)

    def get_success_url(self):
        return reverse_lazy('a_projects:list')


@login_required
def project_delete_confirm_htmx(request, pk):
    """HTMX partial for delete confirmation"""
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    return render(request, 'a_projects/partials/delete_confirm.html', {'project': project})


@login_required
def project_create_htmx(request):
    """HTMX partial for project create form"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        project_type = request.POST.get('type')
        if name and project_type in [Project.TYPE_EMAIL, Project.TYPE_LINKEDIN_DM]:
            project = Project.objects.create(
                name=name,
                type=project_type,
                owner=request.user
            )
            response = render(request, 'a_projects/partials/project_row.html', {'project': project})
            response['HX-Trigger'] = 'projectCreated'
            return response
    return render(request, 'a_projects/partials/create_form.html')