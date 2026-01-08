# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.core.management.base import BaseCommand
from training_provisioner.models.course import Course
from training_provisioner.models.enrollment import Enrollment
from uw_canvas import MissingAccountID
from uw_canvas.sis_import import SISImport, SIS_IMPORTS_API
from datetime import datetime, timedelta, timezone
import json
import re
import logging


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Re-prioritize failed enrollment imports"

    def handle(self, *args, **options):
        latest_import = self.get_most_recent_import()

        if (latest_import
            and latest_import['progress'] == 100
            and latest_import[
                  'workflow_state'] == 'imported_with_messages'):
            self.process_enrollment_errors(latest_import['id'])

    def process_enrollment_errors(self, import_id):
        for sis_error in self.get_import_errors(import_id):
            if sis_error['file'] == 'enrollments.csv':
                if sis_error['message'].startswith(
                        'User not found for enrollment'):
                    self.prioritize_enrollment(sis_error)

    def prioritize_enrollment(self, sis_error):
        try:
            row_info = sis_error.get('row_info', '[{}]')
            row = self.get_csv_row(row_info)
            integration_id = row['user_integration_id']
            course_id = row['course_id']

            course = Course.objects.get(course_id=course_id)
            enrollment = Enrollment.objects.get(
                integration_id=integration_id,
                course__course_id=course_id)

            # Mark enrollment's course to trigger import
            if course.priority == Course.PRIORITY_NONE:
                course.priority = Course.PRIORITY_DEFAULT
                course.save()
                logger.info(f"update course {course_id} priority")

            # Reset enrollment to unprovisioned state
            enrollment.provisioned_date = None
            enrollment.priority = Enrollment.PRIORITY_DEFAULT
            enrollment.save()
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

    def get_most_recent_import(self):
        """
        Get most recent Canvas sis import

        https://developerdocs.instructure.com/services/canvas/resources/sis_imports#method.sis_imports_api.index
        """
        canvas_api = SISImport(per_page=100)
        if not canvas_api._canvas_account_id:
            raise MissingAccountID()

        url = SIS_IMPORTS_API.format(canvas_api._canvas_account_id)
        data_key = 'sis_imports'

        now_utc = datetime.now(timezone.utc)
        three_days_ago = now_utc - timedelta(days=3)
        params = {
            'created_since': three_days_ago.isoformat()
        }

        imports = canvas_api._get_paged_resource(
                url, params=params, data_key=data_key).get(data_key, [])

        most_recent = None
        for imp in imports:
            if not most_recent or imp['id'] > most_recent['id']:
                most_recent = imp

        return most_recent

    def get_import_errors(self, import_id):
        """
        Get errors associated with Canvas import id

        https://developerdocs.instructure.com/services/canvas/resources/sis_import_errors
        """

        canvas_api = SISImport(per_page=100)
        data_key = 'sis_import_errors'

        if not canvas_api._canvas_account_id:
            raise MissingAccountID()

        url = SIS_IMPORTS_API.format(
            canvas_api._canvas_account_id) + "/{}/errors".format(import_id)

        return canvas_api._get_paged_resource(
            url, data_key=data_key).get(data_key, [])
