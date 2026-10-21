from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView

from a_contacts.models import Contact, ContactStepPrompt
from a_generation.models import GeneratedAIField, GeneratedMessage
from a_projects.models import Project, Settings
from a_sequences.models import AIPromptConfig, SequenceStep, Template, TemplateCondition


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.object

        context['steps_count'] = project.sequence_steps.count()
        context['templates_count'] = Template.objects.filter(sequence_step__project=project).count()
        context['conditions_count'] = TemplateCondition.objects.filter(template__sequence_step__project=project).count()
        context['ai_configs_count'] = AIPromptConfig.objects.filter(template__sequence_step__project=project).count()
        context['contacts_count'] = project.contacts.count()
        context['contact_prompts_count'] = ContactStepPrompt.objects.filter(contact__project=project).count()
        context['ai_fields_count'] = GeneratedAIField.objects.filter(contact__project=project).count()
        context['messages_count'] = GeneratedMessage.objects.filter(contact__project=project).count()

        return context


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = 'a_projects/detail.html'
    context_object_name = 'project'

    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user)


@login_required
def project_delete_confirm_htmx(request, pk):
    """HTMX partial for delete confirmation - lists what will be removed."""
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    
    # Count related objects that will be cascade-deleted
    steps_count = project.sequence_steps.count()
    templates_count = 0
    conditions_count = 0
    ai_configs_count = 0
    contacts_count = project.contacts.count()
    contact_prompts_count = 0
    ai_fields_count = 0
    messages_count = 0
    
    if steps_count:
        templates_count = Template.objects.filter(sequence_step__project=project).count()
        conditions_count = TemplateCondition.objects.filter(template__sequence_step__project=project).count()
        ai_configs_count = AIPromptConfig.objects.filter(template__sequence_step__project=project).count()
    
    if contacts_count:
        contact_prompts_count = ContactStepPrompt.objects.filter(contact__project=project).count()
        ai_fields_count = GeneratedAIField.objects.filter(contact__project=project).count()
        messages_count = GeneratedMessage.objects.filter(contact__project=project).count()
    
    context = {
        'project': project,
        'steps_count': steps_count,
        'templates_count': templates_count,
        'conditions_count': conditions_count,
        'ai_configs_count': ai_configs_count,
        'contacts_count': contacts_count,
        'contact_prompts_count': contact_prompts_count,
        'ai_fields_count': ai_fields_count,
        'messages_count': messages_count,
        'total_related': (
            steps_count + templates_count + conditions_count + ai_configs_count +
            contacts_count + contact_prompts_count + ai_fields_count + messages_count
        ),
    }
    return render(request, 'a_projects/partials/delete_confirm.html', context)


@login_required
def project_create_htmx(request):
    """HTMX partial for project create form"""
    errors = []
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
        else:
            if not name:
                errors.append('Project name is required.')
            if project_type not in [Project.TYPE_EMAIL, Project.TYPE_LINKEDIN_DM]:
                errors.append('Please select a valid project type.')
    return render(request, 'a_projects/partials/create_form.html', {'errors': errors})


@login_required
def settings_view(request):
    """Settings page - GET shows current key, POST updates it."""
    settings_obj = Settings.get_settings()

    if request.method == 'POST':
        api_key = request.POST.get('gemini_api_key', '').strip()
        settings_obj.gemini_api_key = api_key
        settings_obj.save()
        messages.success(request, 'Settings saved successfully.')
        settings_obj = Settings.get_settings()

    return render(request, 'a_projects/settings.html', {'settings': settings_obj})