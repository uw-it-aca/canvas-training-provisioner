# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.core.management.base import BaseCommand
from training_provisioner.models import Course, Enrollment


class Command(BaseCommand):
    help = "Import Canvas Training Courses to Canvas"

    def add_arguments(self, parser):
        parser.add_argument(
            'priority', type=int, default=Course.PRIORITY_DEFAULT,
            choices=[Course.PRIORITY_DEFAULT,
                     Course.PRIORITY_IMMEDIATE],
            help='Import courses with priority <priority>')

    def handle(self, *args, **options):
        priority = options.get('priority')
        try:
            imp = Course.objects.queue_by_priority(priority)
        except EmptyQueueException as ex:
            self.update_job()
            return

        try:
            builder = CourseBuilder(imp.queued_objects())
            imp.csv_path = builder.build()
        except Exception:
            imp.csv_errors = traceback.format_exc()

        imp.save()

        try:
            imp.import_csv()
        except MissingImportPathException as ex:
            if not imp.csv_errors:
                imp.delete()

