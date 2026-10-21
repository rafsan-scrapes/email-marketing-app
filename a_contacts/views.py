import csv
from io import TextIOWrapper

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from a_projects.models import Project
from a_contacts.models import Contact, ContactStepPrompt
from a_sequences.models import SequenceStep
from a_generation.models import GeneratedAIField, GeneratedMessage
from a_generation.resolution import resolve_template_for_contact, get_expected_output_placeholders, substitute_template_placeholders, _build_prompt_with_substitutions
from a_generation.gemini_client import call_gemini
from a_sequences.ai_formatting import build_gemini_prompt
from a_sequences.placeholders import extract_placeholders, get_prompt_manual_inputs


def _parse_csv(csv_file):
    """Parse CSV file and return (headers, rows) tuple."""
    # Seek to beginning if possible
    if hasattr(csv_file, 'seek'):
        csv_file.seek(0)
    
    wrapper = TextIOWrapper(csv_file.file, encoding='utf-8')
    reader = csv.DictReader(wrapper)
    headers = reader.fieldnames or []
    rows = list(reader)
    return headers, rows


def _merge_headers(existing_headers, new_headers):
    """Merge header lists: union preserving existing order, then appending new ones."""
    seen = set(existing_headers)
    merged = list(existing_headers)
    for header in new_headers:
        if header not in seen:
            merged.append(header)
            seen.add(header)
    return merged


def _normalize_key_value(value):
    """Normalize key column value for comparison: strip whitespace, lowercase."""
    if value is None:
        return ''
    return str(value).strip().lower()


def _get_suggested_key(project, headers):
    """Get suggested key column based on project type and available headers."""
    if project.type == Project.TYPE_EMAIL:
        return 'email' if 'email' in headers else None
    elif project.type == Project.TYPE_LINKEDIN_DM:
        return 'linkedin' if 'linkedin' in headers else None
    return None


@login_required
def csv_upload_view(request, project_pk):
    """CSV upload form for a project - handles initial upload and re-upload merge."""
    project = get_object_or_404(Project, pk=project_pk, owner=request.user)

    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
        key_column = request.POST.get('key_column', '').strip()

        if not csv_file:
            messages.error(request, 'Please select a CSV file.')
            return redirect('a_contacts:upload', project_pk=project.pk)

        if not key_column:
            messages.error(request, 'Please select a key column.')
            return redirect('a_contacts:upload', project_pk=project.pk)

        # Parse CSV - get both headers and rows in one pass
        try:
            headers, rows = _parse_csv(csv_file)
        except Exception as e:
            messages.error(request, f'Error parsing CSV: {e}')
            return redirect('a_contacts:upload', project_pk=project.pk)

        if not headers:
            messages.error(request, 'CSV file appears to be empty or has no headers.')
            return redirect('a_contacts:upload', project_pk=project.pk)

        if key_column not in headers:
            messages.error(request, f'Selected key column "{key_column}" not found in CSV headers.')
            return redirect('a_contacts:upload', project_pk=project.pk)

        # Check if this is a re-upload (project already has key_column set)
        is_reupload = bool(project.key_column)

        if is_reupload:
            # For re-upload, key_column must match the project's existing key_column
            if key_column != project.key_column:
                messages.error(request, f'Key column must be "{project.key_column}" (already set for this project).')
                return redirect('a_contacts:upload', project_pk=project.pk)

            # Get existing contacts' key values for comparison
            existing_key_values = set()
            for contact in project.contacts.all():
                key_val = contact.data.get(project.key_column)
                existing_key_values.add(_normalize_key_value(key_val))

            # Merge headers
            merged_headers = _merge_headers(project.csv_columns, headers)

            # Insert only new contacts
            contacts_created = 0
            contacts_skipped = 0
            for row in rows:
                normalized_row = {k.strip(): v.strip() if isinstance(v, str) else v for k, v in row.items()}
                key_val = normalized_row.get(key_column)
                normalized_key = _normalize_key_value(key_val)

                if normalized_key in existing_key_values:
                    contacts_skipped += 1
                    continue

                Contact.objects.create(
                    project=project,
                    data=normalized_row,
                    current_step=0,
                )
                contacts_created += 1
                existing_key_values.add(normalized_key)

            # Update project with merged headers
            project.csv_columns = merged_headers
            project.save()

            if contacts_created > 0:
                messages.success(request, f'{contacts_created} new contact{"s" if contacts_created != 1 else ""} added, {contacts_skipped} already existed and {"were" if contacts_skipped != 1 else "was"} left unchanged.')
            else:
                messages.info(request, f'No new contacts added. {contacts_skipped} contact{"s" if contacts_skipped != 1 else ""} already existed and {"were" if contacts_skipped != 1 else "was"} left unchanged.')

        else:
            # Initial upload - create all contacts
            project.csv_columns = headers
            project.key_column = key_column
            project.save()

            contacts_created = 0
            for row in rows:
                normalized_row = {k.strip(): v.strip() if isinstance(v, str) else v for k, v in row.items()}
                Contact.objects.create(
                    project=project,
                    data=normalized_row,
                    current_step=0,
                )
                contacts_created += 1

            messages.success(request, f'Successfully imported {contacts_created} contact{"s" if contacts_created != 1 else ""}.')
        
        return redirect('a_projects:detail', pk=project.pk)

    # GET - show upload form with header dropdown
    # For re-upload, pre-select the existing key_column
    suggested_key = project.key_column if project.key_column else _get_suggested_key(project, project.csv_columns)

    context = {
        'project': project,
        'headers': project.csv_columns,
        'suggested_key': suggested_key,
        'is_reupload': bool(project.key_column),
    }
    return render(request, 'a_contacts/upload.html', context)


@login_required
@csrf_exempt
def csv_headers_htmx(request, project_pk):
    """HTMX endpoint: parse uploaded CSV and return key column dropdown options."""
    project = get_object_or_404(Project, pk=project_pk, owner=request.user)

    csv_file = request.FILES.get('csv_file')
    if not csv_file:
        return render(request, 'a_contacts/partials/key_column_dropdown.html', {'headers': [], 'suggested_key': None, 'is_reupload': False})

    try:
        headers, _ = _parse_csv(csv_file)
    except Exception:
        headers = []

    suggested_key = _get_suggested_key(project, headers)
    is_reupload = bool(project.key_column)
    return render(request, 'a_contacts/partials/key_column_dropdown.html', {'headers': headers, 'suggested_key': suggested_key, 'is_reupload': is_reupload})


@login_required
def contacts_list_view(request, project_pk):
    """Read-only table view of contacts for a project."""
    project = get_object_or_404(Project, pk=project_pk, owner=request.user)
    contacts = Contact.objects.filter(project=project).order_by('created_at')

    context = {
        'project': project,
        'contacts': contacts,
        'columns': project.csv_columns,
    }
    return render(request, 'a_contacts/list.html', context)


@login_required
def dashboard_view(request, project_pk):
    """
    Per-project dashboard showing all contacts with their AI field status and
    message status for the selected sequence step.
    """
    project = get_object_or_404(Project, pk=project_pk, owner=request.user)
    
    # Get the selected step (default to first step if not specified)
    step_pk = request.GET.get('step')
    if step_pk:
        selected_step = get_object_or_404(SequenceStep, pk=step_pk, project=project)
    else:
        selected_step = SequenceStep.objects.filter(project=project).order_by('order').first()
    
    if not selected_step:
        messages.warning(request, 'No sequence steps found for this project. Please create steps first.')
        return redirect('a_projects:detail', pk=project.pk)
    
    # Get all steps for the selector
    steps = SequenceStep.objects.filter(project=project).order_by('order')
    
    # Get all contacts for this project
    contacts = Contact.objects.filter(project=project).order_by('created_at')
    
    # For each contact, get their AI field status and message status for the selected step
    contacts_data = []
    for contact in contacts:
        # Get the key column value for display
        key_value = ''
        if project.key_column:
            key_value = contact.data.get(project.key_column, '')
        
        # Get the template that would be used for this contact at the selected step
        from a_sequences.models import SequenceStep as SeqStep
        step = get_object_or_404(SequenceStep, pk=selected_step.pk, project=project)
        template = resolve_template_for_contact(contact, step)
        
        # Get AI field statuses for this contact/step/template
        from a_generation.resolution import get_expected_output_placeholders
        csv_columns = project.csv_columns
        expected_outputs = get_expected_output_placeholders(template, csv_columns)
        
        ai_status = 'not_generated'
        ai_fields = []
        if expected_outputs:
            ai_fields = list(
                GeneratedAIField.objects.filter(
                    contact=contact,
                    template=template
                ).values('placeholder_name', 'status', 'value', 'error_message'))
            if ai_fields:
                statuses = {f['status'] for f in ai_fields}
                if all(s == 'success' for s in statuses):
                    ai_status = 'success'
                elif any(s == 'error' for s in statuses):
                    ai_status = 'error'
                else:
                    ai_status = 'partial'
            else:
                ai_status = 'not_generated'
        
        # Get message status
        from a_generation.models import GeneratedMessage
        msg = GeneratedMessage.objects.filter(
            contact=contact,
            sequence_step=selected_step
        ).first()
        msg_status = 'generated' if msg else 'not_generated'
        
        # Get or create contact step prompt
        prompt_obj, _ = ContactStepPrompt.objects.get_or_create(
            contact=contact,
            sequence_step=selected_step,
            defaults={'prompt_text': ''}
        )
        
        contacts_data.append({
            'contact': contact,
            'key_value': key_value,
            'ai_status': ai_status,
            'ai_fields': ai_fields,
            'msg_status': msg_status,
            'msg': msg,
            'prompt': prompt_obj,
        })
    
    context = {
        'project': project,
        'steps': steps,
        'selected_step': selected_step,
        'contacts_data': contacts_data,
    }
    return render(request, 'a_contacts/dashboard.html', context)


@login_required
def prompt_override_htmx(request, project_pk, contact_pk, step_pk):
    """HTMX partial to edit a contact's prompt override for a specific step."""
    project = get_object_or_404(Project, pk=project_pk, owner=request.user)
    contact = get_object_or_404(Contact, pk=contact_pk, project=project)
    step = get_object_or_404(SequenceStep, pk=step_pk, project=project)
    
    prompt_obj, _ = ContactStepPrompt.objects.get_or_create(
        contact=contact,
        sequence_step=step,
        defaults={'prompt_text': ''}
    )
    
    if request.method == 'POST':
        prompt_text = request.POST.get('prompt_text', '').strip()
        prompt_obj.prompt_text = prompt_text
        prompt_obj.save()
        messages.success(request, 'Prompt updated.')
        return HttpResponseRedirect(reverse('a_contacts:dashboard', args=[project.pk]) + f'?step={step.pk}')
    
    context = {
        'project': project,
        'contact': contact,
        'step': step,
        'prompt': prompt_obj,
    }
    return render(request, 'a_contacts/partials/prompt_override.html', context)


@login_required
@require_POST
def bulk_send_prompt_view(request, project_pk):
    """
    Bulk action: Send Prompt for selected contacts at the selected step.
    Loops through selected contacts and runs AI field generation for each.
    """
    project = get_object_or_404(Project, pk=project_pk, owner=request.user)
    
    # Get selected step
    step_pk = request.POST.get('step')
    if not step_pk:
        messages.error(request, 'No step selected.')
        return redirect('a_contacts:dashboard', project_pk=project.pk)
    
    selected_step = get_object_or_404(SequenceStep, pk=step_pk, project=project)
    
    # Get selected contact IDs
    contact_ids = request.POST.getlist('contact_ids')
    if not contact_ids:
        messages.error(request, 'No contacts selected.')
        return redirect('a_contacts:dashboard', project_pk=project.pk)
    
    contacts = Contact.objects.filter(pk__in=contact_ids, project=project)
    
    success_count = 0
    error_count = 0
    
    for contact in contacts:
        # Resolve template for this contact/step
        template = resolve_template_for_contact(contact, selected_step)
        
        # Get expected outputs
        csv_columns = project.csv_columns
        expected_outputs = get_expected_output_placeholders(template, contact.project.csv_columns)
        
        if not expected_outputs:
            # No AI-sourced placeholders, skip
            success_count += 1
            continue
        
        # Check for contact-level prompt override
        base_prompt = None
        try:
            contact_prompt_obj = ContactStepPrompt.objects.get(
                contact=contact,
                sequence_step=selected_step
            )
            if contact_prompt_obj.prompt_text:
                base_prompt = contact_prompt_obj.prompt_text
        except ContactStepPrompt.DoesNotExist:
            pass
        
        # Fall back to template AI config
        ai_config = None
        try:
            ai_config = template.ai_prompt_config
        except:
            pass
        
        if not base_prompt:
            base_prompt = ai_config.prompt_text if ai_config else ''
        
        if not base_prompt:
            # No prompt available
            error_count += 1
            continue
        
        # Get manual inputs from base prompt
        manual_inputs = get_prompt_manual_inputs(base_prompt, csv_columns) if base_prompt else []
        manual_values = {}
        
        # Build prompt with substitutions
        prompt = _build_prompt_with_substitutions(base_prompt, contact, manual_values)
        
        # Apply auto-formatting
        formatted_prompt = build_gemini_prompt(prompt, expected_outputs)
        
        # Call Gemini
        result = call_gemini(formatted_prompt)
        
        if not result.success:
            # Save error for all expected outputs
            for field_name in expected_outputs:
                GeneratedAIField.objects.update_or_create(
                    contact=contact,
                    template=template,
                    placeholder_name=field_name,
                    defaults={
                        'value': '',
                        'status': GeneratedAIField.STATUS_ERROR,
                        'error_message': result.error_message,
                    }
                )
            error_count += 1
            continue
        
        # Parse the response
        try:
            parsed = parse_gemini_response(result.raw_text, expected_outputs)
        except ValueError as e:
            for field_name in expected_outputs:
                GeneratedAIField.objects.update_or_create(
                    contact=contact,
                    template=template,
                    placeholder_name=field_name,
                    defaults={
                        'value': '',
                        'status': GeneratedAIField.STATUS_ERROR,
                        'error_message': str(e),
                    }
                )
            error_count += 1
            continue
        
        # Save successful results
        for field_name in expected_outputs:
            GeneratedAIField.objects.update_or_create(
                contact=contact,
                template=template,
                placeholder_name=field_name,
                defaults={
                    'value': parsed.get(field_name, ''),
                    'status': GeneratedAIField.STATUS_SUCCESS,
                    'error_message': '',
                }
            )
        
        success_count += 1
    
    if success_count > 0:
        messages.success(request, f'Successfully generated AI fields for {success_count} contact(s).')
    if error_count > 0:
        messages.error(request, f'Failed to generate AI fields for {error_count} contact(s).')
    
    return HttpResponseRedirect(reverse('a_contacts:dashboard', args=[project.pk]) + f'?step={step_pk}')


@login_required
@require_POST
def bulk_generate_email_dm_view(request, project_pk):
    """
    Bulk action: Generate Email/DM for selected contacts at the selected step.
    Loops through selected contacts and generates email/DM for each.
    """
    project = get_object_or_404(Project, pk=project_pk, owner=request.user)
    
    # Get selected step
    step_pk = request.POST.get('step')
    if not step_pk:
        messages.error(request, 'No step selected.')
        return redirect('a_contacts:dashboard', project_pk=project.pk)
    
    selected_step = get_object_or_404(SequenceStep, pk=step_pk, project=project)
    
    # Get selected contact IDs
    contact_ids = request.POST.getlist('contact_ids')
    if not contact_ids:
        messages.error(request, 'No contacts selected.')
        return HttpResponseRedirect(reverse('a_contacts:dashboard', args=[project.pk]) + f'?step={step_pk}')
    
    contacts = Contact.objects.filter(pk__in=contact_ids, project=project)
    
    success_count = 0
    error_count = 0
    
    for contact in contacts:
        # Resolve the appropriate template for this contact
        template = resolve_template_for_contact(contact, selected_step)
        
        csv_columns = contact.project.csv_columns
        expected_outputs = get_expected_output_placeholders(template, contact.project.csv_columns)
        
        try:
            subject, body = substitute_template_placeholders(template, contact, csv_columns)
        except ValueError as e:
            error_count += 1
            continue
        
        # Save/overwrite GeneratedMessage
        GeneratedMessage.objects.update_or_create(
            contact=contact,
            sequence_step=selected_step,
            defaults={
                'template_used': template,
                'subject': subject,
                'body': body,
            }
        )
        
        # Update contact's current_step and next_due_date (suggestion only, per architecture)
        next_step = SequenceStep.objects.filter(
            project=contact.project,
            order=selected_step.order + 1
        ).first()
        
        if next_step:
            contact.current_step = next_step.order
            from datetime import timedelta
            contact.next_due_date = (timezone.now().date() + timedelta(days=next_step.default_due_offset_days))
            contact.save(update_fields=['current_step', 'next_due_date'])
        
        success_count += 1
    
    if success_count > 0:
        messages.success(request, f'Successfully generated Email/DM for {success_count} contact(s).')
    if error_count > 0:
        messages.error(request, f'Failed to generate Email/DM for {error_count} contact(s).')
    
    return HttpResponseRedirect(reverse('a_contacts:dashboard', args=[project.pk]) + f'?step={step_pk}')


@login_required
def message_modal_view(request, project_pk, contact_pk):
    """HTMX partial to show all messages for a contact across all steps."""
    project = get_object_or_404(Project, pk=project_pk, owner=request.user)
    contact = get_object_or_404(Contact, pk=contact_pk, project=project)
    
    messages_qs = GeneratedMessage.objects.filter(
        contact=contact
    ).select_related('sequence_step', 'template_used').order_by('sequence_step__order')
    
    context = {
        'project': project,
        'contact': contact,
        'messages': messages_qs,
    }
    return render(request, 'a_contacts/partials/message_modal.html', context)