"""Shared placeholder parsing utility for templates and AI prompts."""

import re
from typing import List, Set


def extract_placeholders(text: str) -> List[str]:
    """
    Extract all {{...}} placeholders from text.
    
    Returns unique placeholders in first-seen order, with whitespace trimmed.
    """
    if not text:
        return []
    
    # Find all {{...}} patterns
    pattern = r'\{\{\s*([^}]+?)\s*\}\}'
    matches = re.findall(pattern, text)
    
    # Trim whitespace and deduplicate while preserving order
    seen: Set[str] = set()
    result = []
    for match in matches:
        placeholder = match.strip()
        if placeholder and placeholder not in seen:
            seen.add(placeholder)
            result.append(placeholder)
    
    return result


def classify_placeholders(placeholders: List[str], csv_columns: List[str]) -> dict:
    """
    Classify placeholders as CSV-sourced or AI-sourced.
    
    A placeholder is CSV-sourced if it case-insensitively matches a column
    in csv_columns. Otherwise it's AI-sourced.
    
    Returns dict with 'csv' and 'ai' keys containing lists of placeholder names.
    """
    # Normalize CSV columns for case-insensitive comparison
    csv_columns_lower = {col.strip().lower(): col for col in csv_columns}
    
    csv_sourced = []
    ai_sourced = []
    
    for placeholder in placeholders:
        if placeholder.strip().lower() in csv_columns_lower:
            csv_sourced.append(placeholder)
        else:
            ai_sourced.append(placeholder)
    
    return {
        'csv': csv_sourced,
        'ai': ai_sourced,
    }


def get_placeholder_classification(text: str, csv_columns: List[str]) -> dict:
    """
    Convenience function to extract and classify placeholders from text.
    """
    placeholders = extract_placeholders(text)
    return classify_placeholders(placeholders, csv_columns)


def get_prompt_manual_inputs(prompt_text: str, csv_columns: List[str]) -> List[str]:
    """
    Extract manual input fields from an AI prompt.
    
    Any {{token}} in the prompt that is NOT a CSV column is a manual input.
    Returns list of manual input field names (unique, in first-seen order).
    """
    if not prompt_text:
        return []
    
    # Extract all placeholders from prompt
    placeholders = extract_placeholders(prompt_text)
    
    # Normalize CSV columns for case-insensitive comparison
    csv_columns_lower = {col.strip().lower(): col for col in csv_columns}
    
    # Manual inputs are placeholders that DON'T match CSV columns
    manual_inputs = []
    seen: Set[str] = set()
    
    for placeholder in placeholders:
        if placeholder.strip().lower() not in csv_columns_lower:
            if placeholder not in seen:
                seen.add(placeholder)
                manual_inputs.append(placeholder)
    
    return manual_inputs