from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models, transaction
from django.shortcuts import get_object_or_404, redirect, render

from a_projects.models import Project
from a_sequences.models import SequenceStep


@login_required
def sequence_configure_view(request, project_pk):
    """Sequence configuration view for a project."""
    project = get_object_or_404(Project, pk=project_pk, owner=request.user)
    steps = SequenceStep.objects.filter(project=project).order_by('order')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_initial':
            # Create initial steps from number input
            num_steps = int(request.POST.get('num_steps', 0))
            if num_steps > 0:
                with transaction.atomic():
                    for i in range(num_steps):
                        SequenceStep.objects.create(
                            project=project,
                            name=f'Step {i + 1}',
                            order=i,
                            default_due_offset_days=2,
                        )
                messages.success(request, f'Created {num_steps} sequence steps.')
                return redirect('a_sequences:configure', project_pk=project.pk)
            else:
                messages.error(request, 'Please enter a valid number of steps.')

        elif action == 'add_step':
            # Add a single step at the end
            max_order = steps.aggregate(models.Max('order'))['order__max'] or -1
            SequenceStep.objects.create(
                project=project,
                name=f'Step {max_order + 2}',
                order=max_order + 1,
                default_due_offset_days=2,
            )
            messages.success(request, 'Step added.')
            return redirect('a_sequences:configure', project_pk=project.pk)

        elif action == 'update_steps':
            # Update multiple steps (name, due offset, order)
            step_data = {}
            for key, value in request.POST.items():
                if key.startswith('step_'):
                    parts = key.split('_')
                    if len(parts) >= 3:
                        step_id = int(parts[1])
                        field = '_'.join(parts[2:])
                        if step_id not in step_data:
                            step_data[step_id] = {}
                        step_data[step_id][field] = value

            with transaction.atomic():
                for step_id, data in step_data.items():
                    try:
                        step = SequenceStep.objects.get(pk=step_id, project=project)
                        if 'name' in data:
                            step.name = data['name'].strip()
                        if 'default_due_offset_days' in data:
                            step.default_due_offset_days = int(data['default_due_offset_days'])
                        if 'order' in data:
                            step.order = int(data['order'])
                        step.save()
                    except (SequenceStep.DoesNotExist, ValueError):
                        pass
            messages.success(request, 'Steps updated.')
            return redirect('a_sequences:configure', project_pk=project.pk)

        elif action == 'delete_step':
            step_id = request.POST.get('step_id')
            try:
                step = SequenceStep.objects.get(pk=step_id, project=project)
                step.delete()
                # Reorder remaining steps
                remaining = SequenceStep.objects.filter(project=project).order_by('order')
                for idx, s in enumerate(remaining):
                    s.order = idx
                    s.save()
                messages.success(request, 'Step deleted.')
            except SequenceStep.DoesNotExist:
                messages.error(request, 'Step not found.')
            return redirect('a_sequences:configure', project_pk=project.pk)

        elif action == 'reorder':
            # Handle drag-drop reorder via HTMX
            step_ids = request.POST.getlist('step_order[]')
            with transaction.atomic():
                for idx, step_id in enumerate(step_ids):
                    try:
                        step = SequenceStep.objects.get(pk=step_id, project=project)
                        step.order = idx
                        step.save()
                    except SequenceStep.DoesNotExist:
                        pass
            return render(request, 'a_sequences/partials/step_list.html', {'steps': SequenceStep.objects.filter(project=project).order_by('order')})

    context = {
        'project': project,
        'steps': steps,
    }
    return render(request, 'a_sequences/configure.html', context)