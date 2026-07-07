import csv
import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.shortcuts import render

from examinations.models import Exam
from .csv_import import IMPORT_TYPES


def import_manager_check(user):
    return user.is_authenticated and user.role in ['admin', 'headteacher', 'bursar']


@login_required
@user_passes_test(import_manager_check)
def import_hub(request):
    import_type = request.GET.get('type', 'students')
    if import_type not in IMPORT_TYPES:
        import_type = 'students'
    meta = IMPORT_TYPES[import_type]
    result = None
    exams = Exam.objects.select_related('subject', 'class_room', 'term').order_by('-start_date')

    if request.method == 'POST':
        uploaded = request.FILES.get('csv_file')
        if not uploaded:
            messages.error(request, 'Please select a CSV file to upload.')
        elif not uploaded.name.lower().endswith('.csv'):
            messages.error(request, 'Only .csv files are supported. Save your Excel sheet as CSV first.')
        else:
            post_type = request.POST.get('import_type', import_type)
            if post_type not in IMPORT_TYPES:
                messages.error(request, 'Invalid import type.')
            else:
                handler = IMPORT_TYPES[post_type]['handler']
                kwargs = {}
                if post_type == 'exam_marks':
                    exam_id = request.POST.get('exam_id')
                    if exam_id:
                        kwargs['exam_id'] = int(exam_id)
                elif post_type == 'payments':
                    kwargs['recorded_by'] = request.user
                try:
                    result = handler(uploaded, **kwargs)
                    if result['errors']:
                        messages.warning(
                            request,
                            f"Import finished with {result['created']} created, "
                            f"{result.get('updated', 0)} updated, {result['errors']} error(s).",
                        )
                    else:
                        messages.success(
                            request,
                            f"Successfully imported {result['created']} record(s)"
                            + (f", updated {result['updated']}" if result.get('updated') else '') + '.',
                        )
                    import_type = post_type
                    meta = IMPORT_TYPES[import_type]
                except ValueError as exc:
                    messages.error(request, str(exc))

    return render(request, 'core/import_data.html', {
        'import_types': IMPORT_TYPES,
        'current_type': import_type,
        'meta': meta,
        'result': result,
        'exams': exams,
    })


@login_required
@user_passes_test(import_manager_check)
def download_import_template(request, import_type):
    if import_type not in IMPORT_TYPES:
        return HttpResponse('Unknown template', status=404)

    meta = IMPORT_TYPES[import_type]
    sample_lines = meta['sample'].strip().split('\n')
    reader = csv.reader(sample_lines)
    rows = list(reader)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    for row in rows:
        writer.writerow(row)

    response = HttpResponse(buffer.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{import_type}_template.csv"'
    return response