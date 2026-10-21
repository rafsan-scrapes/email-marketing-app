"""Template resolution logic for matching templates to contacts."""

from a_sequences.models import Template, TemplateCondition
from a_sequences.placeholders import extract_placeholders


def resolve_template_for_contact(contact, sequence_step):
    """
    Resolve the appropriate template for a contact at a given sequence step.
    
    Evaluates condition templates in order (by Template.order), returning the
    first one whose conditions all match. Falls back to the default template
    (order=0, no conditions) if none match.
    
    Args:
        contact: Contact instance
        sequence_step: SequenceStep instance
        
    Returns:
        Template instance (never None - default template always exists)
    """
    templates = Template.objects.filter(sequence_step=sequence_step).order_by('order')
    
    for template in templates:
        if template.is_default:
            # Default template has no conditions, always matches as fallback
            continue
        
        if _template_matches_contact(template, contact):
            return template
    
    # Fall back to default template
    return sequence_step.get_default_template()


def _template_matches_contact(template, contact):
    """
    Check if all conditions on a template match the contact's data.
    
    All conditions are ANDed together - all must match for the template to be selected.
    
    Args:
        template: Template instance
        contact: Contact instance
        
    Returns:
        bool: True if all conditions match, False otherwise
    """
    conditions = template.get_conditions_ordered()
    if not conditions:
        return False  # Should not happen for non-default templates
    
    for condition in conditions:
        if not _condition_matches(condition, contact):
            return False
    
    return True


def _condition_matches(condition, contact):
    """
    Check if a single condition matches the contact's data.
    
    Args:
        condition: TemplateCondition instance
        contact: Contact instance
        
    Returns:
        bool: True if condition matches, False otherwise
    """
    column_name = condition.column_name
    operator = condition.operator
    value = condition.value
    
    # Get the contact's value for this column (case-insensitive key lookup)
    contact_value = None
    for key, val in contact.data.items():
        if key.lower() == column_name.lower():
            contact_value = val
            break
    
    if contact_value is None:
        contact_value = ''
    
    contact_str = str(contact_value).strip()
    condition_value = str(value).strip()
    
    if operator == TemplateCondition.OPERATOR_EQUALS:
        return contact_str.lower() == condition_value.lower()
    
    elif operator == TemplateCondition.OPERATOR_NOT_EQUALS:
        return contact_str.lower() != condition_value.lower()
    
    elif operator == TemplateCondition.OPERATOR_CONTAINS:
        return condition_value.lower() in contact_str.lower()
    
    elif operator == TemplateCondition.OPERATOR_IS_EMPTY:
        return contact_str == ''
    
    elif operator == TemplateCondition.OPERATOR_IS_NOT_EMPTY:
        return contact_str != ''
    
    elif operator == TemplateCondition.OPERATOR_GREATER_THAN:
        try:
            return float(contact_str) > float(condition_value)
        except (ValueError, TypeError):
            return False
    
    elif operator == TemplateCondition.OPERATOR_LESS_THAN:
        try:
            return float(contact_str) < float(condition_value)
        except (ValueError, TypeError):
            return False
    
    return False


def get_expected_output_placeholders(template, csv_columns):
    """
    Get the expected AI output placeholder names for a template.
    
    Reuses the placeholder utility to classify placeholders in the template's
    subject and body as CSV-sourced vs AI-sourced.
    
    Args:
        template: Template instance
        csv_columns: List of CSV column names from the project
        
    Returns:
        List of AI-sourced placeholder names (strings)
    """
    from a_sequences.placeholders import extract_placeholders, classify_placeholders
    
    combined_text = ''
    if template.subject:
        combined_text += template.subject + '\n'
    combined_text += template.body
    
    placeholders = extract_placeholders(combined_text)
    classification = classify_placeholders(placeholders, csv_columns)
    return classification['ai']


def parse_gemini_response(raw_text, expected_outputs):
    """
    Parse the Gemini API response to extract tagged output values.
    
    Expects each expected output to be wrapped in <placeholder_name>...</placeholder_name> tags.
    
    Args:
        raw_text: Raw response text from Gemini
        expected_outputs: List of expected placeholder names
        
    Returns:
        dict: Mapping of placeholder_name -> extracted value
        
    Raises:
        ValueError: If any expected tag is missing from the response
    """
    results = {}
    missing = []
    
    for placeholder in expected_outputs:
        start_tag = f"<{placeholder}>"
        end_tag = f"</{placeholder}>"
        
        start_idx = raw_text.find(start_tag)
        if start_idx == -1:
            missing.append(placeholder)
            continue
        
        end_idx = raw_text.find(end_tag, start_idx)
        if end_idx == -1:
            missing.append(placeholder)
            continue
        
        # Extract content between tags
        value_start = start_idx + len(start_tag)
        value = raw_text[value_start:end_idx].strip()
        results[placeholder] = value
    
    if missing:
        raise ValueError(f"Missing tags in Gemini response: {missing}")
    
    return results


def substitute_template_placeholders(template, contact, csv_columns):
    """
    Substitute all placeholders in a template's subject and body.
    
    CSV-sourced placeholders are substituted from contact.data.
    AI-sourced placeholders are substituted from GeneratedAIField (status=success).
    
    Args:
        template: Template instance
        contact: Contact instance
        csv_columns: List of CSV column names from the project
        
    Returns:
        tuple: (subject, body) with all placeholders substituted
        
    Raises:
        ValueError: If any AI-sourced placeholder has no successful saved value
    """
    from a_sequences.placeholders import extract_placeholders, classify_placeholders
    from a_generation.models import GeneratedAIField
    
    combined_text = ''
    if template.subject:
        combined_text += template.subject + '\n'
    combined_text += template.body
    
    placeholders = extract_placeholders(combined_text)
    classification = classify_placeholders(placeholders, csv_columns)
    
    csv_sourced = classification['csv']
    ai_sourced = classification['ai']
    
    subject = template.subject or ''
    body = template.body or ''
    
    # Substitute CSV-sourced placeholders
    for placeholder in csv_sourced:
        value = ''
        for key, val in contact.data.items():
            if key.lower() == placeholder.lower():
                value = str(val)
                break
        subject = subject.replace(f'{{{{{placeholder}}}}}', value)
        body = body.replace(f'{{{{{placeholder}}}}}', value)
    
    # Substitute AI-sourced placeholders from GeneratedAIField
    for placeholder in ai_sourced:
        try:
            ai_field = GeneratedAIField.objects.get(
                contact=contact,
                template=template,
                placeholder_name=placeholder,
                status=GeneratedAIField.STATUS_SUCCESS
            )
            value = ai_field.value
        except GeneratedAIField.DoesNotExist:
            raise ValueError(
                f"AI-sourced placeholder '{{{{{placeholder}}}}}' has no saved value. "
                f"Please run 'Generate AI Fields' for this contact and step first."
            )
        
        subject = subject.replace(f'{{{{{placeholder}}}}}', value)
        body = body.replace(f'{{{{{placeholder}}}}}', value)
    
    return subject, body