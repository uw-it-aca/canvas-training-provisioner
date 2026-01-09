# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.core.management.base import BaseCommand
from training_provisioner.models.course import Course
from training_provisioner.models.enrollment import Enrollment
from training_provisioner.dao.canvas import get_sis_imports, get_import_errors
from datetime import datetime, timedelta, timezone
import json
import re
from logging import getLogger


logger = getLogger(__name__)


class Command(BaseCommand):
    help = "Re-prioritize failed enrollment imports"

    def handle(self, *args, **options):
        latest_import = self.get_most_recent_import()

        if (latest_import
            and latest_import.progress == 100
            and latest_import.workflow_state == 'imported_with_messages'):
            self.process_enrollment_errors(latest_import)

    def process_enrollment_errors(self, sis_import):
        for sis_error in get_import_errors(sis_import):
            if sis_error.import_file == 'enrollments.csv':
                if sis_error.message.startswith(
                        'User not found for enrollment'):
                    self.prioritize_enrollment(sis_error)

    def prioritize_enrollment(self, sis_error):
        try:
            row = self.get_csv_row(sis_error.row_info)
            integration_id = row['user_integration_id']
            course_id = row['course_id']

            course = Course.objects.get(course_id=course_id)
            enrollment = Enrollment.objects.get(
                integration_id=integration_id,
                course__course_id=course_id)

            # Mark enrollment's course to trigger import
            if course.priority == Course.PRIORITY_NONE:
                course.priority = Course.PRIORITY_DEFAULT
#                course.save()
                logger.info(f"update course {course_id} priority")

            # Reset enrollment to unprovisioned state
            enrollment.provisioned_date = None
            enrollment.priority = Enrollment.PRIORITY_DEFAULT
#            enrollment.save()
            logger.info(f"Prioritize enrollment {integration_id} in "
                        f"course {course_id}")

        except Exception as ex:
            logger.error(f"Malformed row ({row_info}) info: {ex}")
        except Course.DoesNotExist:
            logger.error(f"NO Course for {integration_id} in "
                         f"course {course_id}")
        except Enrollment.DoesNotExist:
            logger.error(f"NO Enrollment for {integration_id} in "
                         f"course {course_id}")

    def get_csv_row(self, row_info):
        # map hokey ruby string to json
        json_row = re.sub(
            r'([{ ])([A-Za-z_]+):', '\\1"\\2":', row_info)
        json_row = re.sub(r' nil([,}])', ' null\\1', json_row)
        return json.loads(json_row)[0]

    def get_most_recent_import(self, params={}):
        # disregard imports older than 3 days
        now_utc = datetime.now(timezone.utc)
        three_days_ago = now_utc - timedelta(days=3)
        params = {
            'created_since': three_days_ago.isoformat()
        }

        most_recent = None
        for imp in get_sis_imports(params):
            if not most_recent or imp.import_id > most_recent.import_id:
                most_recent = imp

        return most_recent
