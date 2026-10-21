import csv
from io import TextIOWrapper

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt

from a_projects.models import Project
from a_contacts.models import Contact


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
        return render(request, 'a_contacts/partials/key_column_dropdown.html', {'headers': [], 'suggested_key': None})

    try:
        headers, _ = _parse_csv(csv_file)
    except Exception:
        headers = []

    suggested_key = _get_suggested_key(project, headers)
    return render(request, 'a_contacts/partials/key_column_dropdown.html', {'headers': headers, 'suggested_key': suggested_key})


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