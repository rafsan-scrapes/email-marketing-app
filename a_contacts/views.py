import csv
from io import TextIOWrapper

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from a_projects.models import Project
from a_contacts.models import Contact


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
            wrapper = TextIOWrapper(csv_file.file, encoding='utf-8')
            reader = csv.DictReader(wrapper)
            headers = reader.fieldnames or []
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
    # Pre-select key column based on project type
    suggested_key = None
    if project.type == Project.TYPE_EMAIL:
        suggested_key = 'email' if 'email' in project.csv_columns else None
    elif project.type == Project.TYPE_LINKEDIN_DM:
        suggested_key = 'linkedin' if 'linkedin' in project.csv_columns else None

    # If project already has csv_columns, use those; otherwise we'll parse from file on POST
    context = {
        'project': project,
        'headers': project.csv_columns,
        'suggested_key': suggested_key,
    }
    return render(request, 'a_contacts/upload.html', context)