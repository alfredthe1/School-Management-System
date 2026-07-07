from django.core.management.base import BaseCommand

from staff.demo_data import populate_staff_and_payroll


class Command(BaseCommand):
    help = 'Populate demo staff members (including teachers) and payroll data'

    def handle(self, *args, **options):
        self.stdout.write('Creating demo staff and payroll data...')
        populate_staff_and_payroll(stdout=self.stdout)
        self.stdout.write(self.style.SUCCESS('Staff and payroll demo data ready!'))
        self.stdout.write('')
        self.stdout.write('Teachers can view payroll at: /staff/my-payroll/')
        self.stdout.write('  teacher1 / teacher123')
        self.stdout.write('  teacher2 / teacher123')
        self.stdout.write('  teacher3 / teacher123')
        self.stdout.write('  headteacher / head123')
        self.stdout.write('  bursar / bursar123')