# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.core.management.base import BaseCommand
from training_provisioner.models.training_course import TrainingCourse
from training_provisioner.models.course import Course
from training_provisioner.models.enrollment import Enrollment


class Command(BaseCommand):
    help = "Load Canvas Training Courses"

    def handle(self, *args, **options):
        for course in TrainingCourse.objects.active_courses():
            for course_sis_id in course.get_all_course_sis_import_ids():
                Course.objects.add_course({
                })

            for integration_id in course.get_membership_for_course():
                Enrollment.objects.add_enrollment({
                })

