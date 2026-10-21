from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models, transaction
from django.shortcuts import get_object_or_404, redirect, render

from a_projects.models import Project
from a_sequences.models import SequenceStep, Template, TemplateCondition
from a_sequences.placeholders import extract_placeholders, classify_placeholders


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
                        step = SequenceStep.objects.create(
                            project=project,
                            name=f'Step {i + 1}',
                            order=i,
                            default_due_offset_days=2,
                        )
                        # Create default template for each step
                        Template.objects.create(
                            sequence_step=step,
                            order=0,
                            subject='',
                            body='',
                        )
                messages.success(request, f'Created {num_steps} sequence steps.')
                return redirect('a_sequences:configure', project_pk=project.pk)
            else:
                messages.error(request, 'Please enter a valid number of steps.')

        elif action == 'add_step':
            # Add a single step at the end
            max_order = steps.aggregate(models.Max('order'))['order__max'] or -1
            step = SequenceStep.objects.create(
                project=project,
                name=f'Step {max_order + 2}',
                order=max_order + 1,
                default_due_offset_days=2,
            )
            # Create default template for the new step
            Template.objects.create(
                sequence_step=step,
                order=0,
                subject='',
                body='',
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


@login_required
def template_configure_view(request, project_pk, step_pk):
    """Template configuration view for a sequence step."""
    project = get_object_or_404(Project, pk=project_pk, owner=request.user)
    step = get_object_or_404(SequenceStep, pk=step_pk, project=project)
    templates = Template.objects.filter(sequence_step=step).order_by('order')
    csv_columns = project.csv_columns

    # Ensure default template exists
    default_template = step.get_default_template()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_condition_template':
            # Add a new condition template (order after the default template)
            max_order = templates.aggregate(models.Max('order'))['order__max'] or 0
            new_template = Template.objects.create(
                sequence_step=step,
                order=max_order + 1,
                subject='',
                body='',
            )
            messages.success(request, 'Condition template added.')
            return redirect('a_sequences:template_configure', project_pk=project.pk, step_pk=step.pk)

        elif action == 'delete_template':
            template_id = request.POST.get('template_id')
            try:
                template = Template.objects.get(pk=template_id, sequence_step=step)
                if template.is_default:
                    messages.error(request, 'Cannot delete the default template.')
                else:
                    template.delete()
                    # Reorder remaining templates
                    remaining = Template.objects.filter(sequence_step=step).order_by('order')
                    for idx, t in enumerate(remaining):
                        t.order = idx
                        t.save()
                    messages.success(request, 'Condition template deleted.')
            except Template.DoesNotExist:
                messages.error(request, 'Template not found.')
            return redirect('a_sequences:template_configure', project_pk=project.pk, step_pk=step.pk)

        elif action == 'update_templates':
            # Update templates (subject, body, order) and their conditions
            with transaction.atomic():
                # Update templates
                template_data = {}
                condition_data = {}

                for key, value in request.POST.items():
                    if key.startswith('template_'):
                        parts = key.split('_')
                        if len(parts) >= 3:
                            template_id = int(parts[1])
                            field = '_'.join(parts[2:])
                            if template_id not in template_data:
                                template_data[template_id] = {}
                            template_data[template_id][field] = value
                    elif key.startswith('condition_'):
                        parts = key.split('_')
                        if len(parts) >= 4:
                            template_id = int(parts[1])
                            condition_idx = int(parts[2])
                            field = '_'.join(parts[3:])
                            if template_id not in condition_data:
                                condition_data[template_id] = {}
                            if condition_idx not in condition_data[template_id]:
                                condition_data[template_id][condition_idx] = {}
                            condition_data[template_id][condition_idx][field] = value

                # Process template updates
                for template_id, data in template_data.items():
                    try:
                        template = Template.objects.get(pk=template_id, sequence_step=step)
                        # Don't allow reordering of default template
                        if template.is_default and 'order' in data:
                            continue
                        if 'subject' in data:
                            template.subject = data['subject']
                        if 'body' in data:
                            template.body = data['body']
                        if 'order' in data:
                            template.order = int(data['order'])
                        template.save()
                    except (Template.DoesNotExist, ValueError):
                        pass

                # Process condition updates
                for template_id, conditions in condition_data.items():
                    try:
                        template = Template.objects.get(pk=template_id, sequence_step=step)
                        # Skip condition updates for default template
                        if template.is_default:
                            continue

                        # Delete existing conditions and recreate
                        template.conditions.all().delete()
                        for condition_idx, cond_data in sorted(conditions.items()):
                            if not cond_data.get('column_name'):
                                continue
                            TemplateCondition.objects.create(
                                template=template,
                                order=condition_idx,
                                column_name=cond_data['column_name'],
                                operator=cond_data['operator'],
                                value=cond_data.get('value', ''),
                            )
                    except (Template.DoesNotExist, ValueError):
                        pass

            messages.success(request, 'Templates updated.')
            return redirect('a_sequences:template_configure', project_pk=project.pk, step_pk=step.pk)

        elif action == 'reorder_templates':
            template_ids = request.POST.getlist('template_order[]')
            with transaction.atomic():
                for idx, template_id in enumerate(template_ids):
                    try:
                        template = Template.objects.get(pk=template_id, sequence_step=step)
                        if not template.is_default:
                            template.order = idx
                            template.save()
                    except Template.DoesNotExist:
                        pass
            return render(request, 'a_sequences/partials/template_list.html', {
                'templates': Template.objects.filter(sequence_step=step).order_by('order'),
                'csv_columns': project.csv_columns,
                'step': step,
                'project': project,
            })

    context = {
        'project': project,
        'step': step,
        'templates': templates,
        'csv_columns': csv_columns,
    }
    # Add placeholder classification for each template
    for template in templates:
        # Combine subject and body for placeholder extraction
        combined_text = ''
        if template.subject:
            combined_text += template.subject + '\n'
        combined_text += template.body
        
        placeholders = extract_placeholders(combined_text)
        classification = classify_placeholders(placeholders, csv_columns)
        template.placeholder_classification = classification
    
    return render(request, 'a_sequences/template_configure.html', context)