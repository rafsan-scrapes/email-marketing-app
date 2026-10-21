import csv
from io import TextIOWrapper

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from a_projects.models import Project
from a_contacts.models import Contact


def _parse_csv_headers(csv_file):
    """Parse CSV file and return headers list."""
    wrapper = TextIOWrapper(csv_file.file, encoding='utf-8')
    reader = csv.DictReader(wrapper)
    return reader.fieldnames or []


def _get_suggested_key(project, headers):
    """Get suggested key column based on project type and available headers."""
    if project.type == Project.TYPE_EMAIL:
        return 'email' if 'email' in headers else None
    elif project.type == Project.TYPE_LINKEDIN_DM:
        return 'linkedin' if 'linkedin' in headers else None
    return None


@login_required
def csv_upload_view(request, project_pk):
    """CSV upload form for a project - handles initial upload with key column selection."""
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

        # Parse CSV
        try:
            headers = _parse_csv_headers(csv_file)
            wrapper = TextIOWrapper(csv_file.file, encoding='utf-8')
            reader = csv.DictReader(wrapper)
            rows = list(reader)
        except Exception as e:
            messages.error(request, f'Error parsing CSV: {e}')
            return redirect('a_contacts:upload', project_pk=project.pk)

        if not headers:
            messages.error(request, 'CSV file appears to be empty or has no headers.')
            return redirect('a_contacts:upload', project_pk=project.pk)

        if key_column not in headers:
            messages.error(request, f'Selected key column "{key_column}" not found in CSV headers.')
            return redirect('a_contacts:upload', project_pk=project.pk)

        # Update project with csv_columns and key_column
        project.csv_columns = headers
        project.key_column = key_column
        project.save()

        # Create contacts
        contacts_created = 0
        for row in rows:
            # Normalize row keys to match headers (strip whitespace)
            normalized_row = {k.strip(): v.strip() if isinstance(v, str) else v for k, v in row.items()}
            Contact.objects.create(
                project=project,
                data=normalized_row,
                current_step=0,
            )
            contacts_created += 1

        messages.success(request, f'Successfully imported {contacts_created} contacts.')
        return redirect('a_projects:detail', pk=project.pk)

    # GET - show upload form with header dropdown
    suggested_key = _get_suggested_key(project, project.csv_columns)

    context = {
        'project': project,
        'headers': project.csv_columns,
        'suggested_key': suggested_key,
    }
    return render(request, 'a_contacts/upload.html', context)


@login_required
def csv_headers_htmx(request, project_pk):
    """HTMX endpoint: parse uploaded CSV and return key column dropdown options."""
    project = get_object_or_404(Project, pk=project_pk, owner=request.user)

    csv_file = request.FILES.get('csv_file')
    if not csv_file:
        return render(request, 'a_contacts/partials/key_column_dropdown.html', {'headers': [], 'suggested_key': None})

    try:
        headers = _parse_csv_headers(csv_file)
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