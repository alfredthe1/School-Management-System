from django.db import migrations


def seed_grade_scales(apps, schema_editor):
    GradeScale = apps.get_model('examinations', 'GradeScale')
    if GradeScale.objects.exists():
        return
    scales = [
        ('A', 80, 100, 'Excellent'),
        ('B', 70, 79.99, 'Very Good'),
        ('C', 60, 69.99, 'Good'),
        ('D', 50, 59.99, 'Fair'),
        ('E', 40, 49.99, 'Pass'),
        ('F', 0, 39.99, 'Fail'),
    ]
    for grade, min_s, max_s, remark in scales:
        GradeScale.objects.create(
            name=grade, grade=grade, min_score=min_s, max_score=max_s, remark=remark
        )


class Migration(migrations.Migration):
    dependencies = [
        ('examinations', '0002_alter_exam_options_remove_examresult_subject_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_grade_scales, migrations.RunPython.noop),
    ]