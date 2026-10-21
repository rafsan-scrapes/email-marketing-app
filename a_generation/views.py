from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from a_contacts.models import Contact, ContactStepPrompt
from a_projects.settings_utils import get_gemini_api_key
from a_sequences.models import Template, AIPromptConfig, SequenceStep
from a_sequences.placeholders import get_prompt_manual_inputs
from a_sequences.ai_formatting import build_gemini_prompt
from a_generation.models import GeneratedAIField, GeneratedMessage
from a_generation.gemini_client import call_gemini
from a_generation.resolution import (
    resolve_template_for_contact,
    get_expected_output_placeholders,
    parse_gemini_response,
    substitute_template_placeholders,
    _build_prompt_with_substitutions,
)


@login_required
def generate_ai_fields_view(request, project_pk, contact_pk, step_pk):
    """
    Generate AI fields for a single contact at a specific sequence step.
    
    GET: Shows form with manual input fields for the AI prompt
    POST: Substitutes CSV/manual values into prompt, calls Gemini, parses and saves results
    """
    contact = get_object_or_404(Contact, pk=contact_pk, project_id=project_pk)
    sequence_step = get_object_or_404(contact.project.sequence_steps, pk=step_pk)
    
    # Resolve the appropriate template for this contact
    template = resolve_template_for_contact(contact, contact.project.sequence_steps.get(pk=step_pk))
    
    # Check for contact-level prompt override first, then template default
    contact_prompt_obj = None
    try:
        contact_prompt_obj = ContactStepPrompt.objects.get(contact=contact, sequence_step=sequence_step)
    except ContactStepPrompt.DoesNotExist:
        pass

    # Try template AI prompt config
    ai_config = None
    try:
        ai_config = template.ai_prompt_config
    except AIPromptConfig.DoesNotExist:
        pass

    base_prompt = ''
    if contact_prompt_obj and contact_prompt_obj.prompt_text:
        base_prompt = contact_prompt_obj.prompt_text
    elif ai_config and ai_config.prompt_text:
        base_prompt = ai_config.prompt_text

    # Get expected outputs (AI-sourced placeholders from template)
    csv_columns = contact.project.csv_columns
    expected_outputs = get_expected_output_placeholders(template, csv_columns)
    
    if not expected_outputs:
        messages.info(request, 'The resolved template has no AI-sourced placeholders to generate.')
        return redirect('a_contacts:list', project_pk=contact.project_id)
    
    if not base_prompt:
        messages.error(request, 'No AI prompt available. Please set a prompt using "Set Prompt" in the dashboard, or configure the template AI.')
        return redirect('a_contacts:dashboard', project_pk=contact.project_id)
    
    # Get manual input field names from the resolved prompt text
    manual_inputs = get_prompt_manual_inputs(base_prompt, csv_columns) if base_prompt else []
    
    # Check for contact-specific prompt override (already resolved above)
    # base_prompt already has the correct prompt (contact override or template default)
    
    # Get existing AI fields for this contact/template (for pre-filling on retry)
    existing_fields = {
        f.placeholder_name: f
        for f in GeneratedAIField.objects.filter(contact=contact, template=template)
    }
    
    if request.method == 'POST':
        # Check if this is a retry for a specific field
        retry_field = request.POST.get('retry_field')
        
        if retry_field:
            # Retry just this specific field
            field_names = [retry_field]
            # Re-fetch manual inputs for this field if needed
            manual_values = {retry_field: request.POST.get(retry_field, '')}
        else:
            # Generate all fields
            field_names = expected_outputs
            # Collect manual input values from form
            manual_values = {
                field: request.POST.get(field, '')
                for field in manual_inputs
            }
        
        # Build the prompt with substitutions
        prompt = _build_prompt_with_substitutions(
            base_prompt,
            contact,
            manual_values,
        )
        
        # Apply auto-formatting
        formatted_prompt = build_gemini_prompt(prompt, field_names)
        
        # Call Gemini
        result = call_gemini(formatted_prompt)
        
        if not result.success:
            # Save error for each requested field
            for field_name in field_names:
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
            messages.error(request, f'Gemini error: {result.error_message}')
            return redirect('a_generation:generate_ai_fields', project_pk=project_pk, contact_pk=contact_pk, step_pk=step_pk)
        
        # Parse the response
        try:
            parsed = parse_gemini_response(result.raw_text, field_names)
        except ValueError as e:
            for field_name in field_names:
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
            messages.error(request, f'Failed to parse AI response: {e}')
            return redirect('a_generation:generate_ai_fields', project_pk=project_pk, contact_pk=contact_pk, step_pk=step_pk)
        
        # Save successful results
        for field_name in field_names:
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
        
        if retry_field:
            messages.success(request, f'Successfully generated {retry_field}.')
        else:
            messages.success(request, f'Successfully generated {len(field_names)} AI field(s).')
        
        return redirect('a_generation:generate_ai_fields', project_pk=project_pk, contact_pk=contact_pk, step_pk=step_pk)
    
    # GET request - show form
    manual_input_fields = manual_inputs
    
    context = {
        'contact': contact,
        'template': template,
        'sequence_step': contact.project.sequence_steps.get(pk=step_pk),
        'ai_config': ai_config,
        'expected_outputs': expected_outputs,
        'manual_inputs': manual_input_fields,
        'existing_fields': existing_fields,
        'csv_columns': contact.project.csv_columns,
    }
    return render(request, 'a_generation/generate_ai_fields.html', context)


@login_required
def generate_email_dm_view(request, project_pk, contact_pk, step_pk):
    """
    Generate Email/DM for a single contact at a specific sequence step.
    
    Resolves the template, substitutes all placeholders (CSV from contact.data,
    AI from GeneratedAIField), saves/overwrites GeneratedMessage, and updates
    contact's current_step and next_due_date.
    """
    contact = get_object_or_404(Contact, pk=contact_pk, project_id=project_pk)
    sequence_step = get_object_or_404(contact.project.sequence_steps, pk=step_pk)
    
    # Resolve the appropriate template for this contact
    template = resolve_template_for_contact(contact, sequence_step)
    
    csv_columns = contact.project.csv_columns
    expected_outputs = get_expected_output_placeholders(template, csv_columns)
    
    if request.method == 'POST':
        try:
            subject, body = substitute_template_placeholders(template, contact, csv_columns)
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('a_generation:generate_email_dm', project_pk=project_pk, contact_pk=contact_pk, step_pk=step_pk)
        
        # Save/overwrite GeneratedMessage
        generated_message, created = GeneratedMessage.objects.update_or_create(
            contact=contact,
            sequence_step=sequence_step,
            defaults={
                'template_used': template,
                'subject': subject,
                'body': body,
            }
        )
        
        # Update contact's current_step and next_due_date (suggestion only, per architecture)
        next_step = SequenceStep.objects.filter(
            project=contact.project,
            order=sequence_step.order + 1
        ).first()
        
        if next_step:
            contact.current_step = next_step.order
            from datetime import timedelta
            contact.next_due_date = (timezone.now().date() + timedelta(days=next_step.default_due_offset_days))
            contact.save(update_fields=['current_step', 'next_due_date'])
        
        messages.success(request, 'Email/DM generated successfully.')
        return redirect('a_generation:generate_email_dm', project_pk=project_pk, contact_pk=contact_pk, step_pk=step_pk)
    
    # GET request - show preview
    try:
        subject, body = substitute_template_placeholders(template, contact, csv_columns)
        missing_ai = False
        missing_ai_placeholders = []
    except ValueError as e:
        subject = ''
        body = ''
        missing_ai = True
        missing_ai_placeholders = [str(e)]
    
    csv_columns = contact.project.csv_columns
    expected_outputs = get_expected_output_placeholders(template, csv_columns)
    
    # Check which AI placeholders are missing
    ai_placeholders = []
    for ph in expected_outputs:
        try:
            GeneratedAIField.objects.get(
                contact=contact,
                template=template,
                placeholder_name=ph,
                status=GeneratedAIField.STATUS_SUCCESS
            )
        except GeneratedAIField.DoesNotExist:
            ai_placeholders.append(ph)
    
    context = {
        'contact': contact,
        'template': template,
        'sequence_step': sequence_step,
        'subject': subject,
        'body': body,
        'missing_ai': missing_ai or len(ai_placeholders) > 0,
        'missing_ai_placeholders': ai_placeholders,
        'expected_outputs': expected_outputs,
    }
    return render(request, 'a_generation/generate_email_dm.html', context)

