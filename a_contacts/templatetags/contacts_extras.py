from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary using a variable key."""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def is_csv(placeholder, csv_columns):
    """Check if a placeholder matches a CSV column (case-insensitive)."""
    if not csv_columns:
        return False
    csv_lower = {col.lower(): col for col in csv_columns}
    return placeholder.lower() in csv_lower