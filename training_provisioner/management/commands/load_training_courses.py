# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.core.management.base import BaseCommand
from training_provisioner.models.training_course import TrainingCourse


class Command(BaseCommand):
    help = "Load Canvas Training Courses"

    def handle(self, *args, **options):
        # Get active courses and sort by term_id to process earlier academic
        # years first. This prevents race conditions when checking for
        # previous enrollments
        active_courses = (
            TrainingCourse.objects.active_courses().order_by('term_id'))

        for training_course in active_courses:
            training_course.load_courses_and_enrollments()
