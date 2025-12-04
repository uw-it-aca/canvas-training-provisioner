# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.core.management.base import BaseCommand
from training_provisioner.models.training_course import TrainingCourse
from training_provisioner.models.term import Term
from training_provisioner.models.course import Course
from training_provisioner.models.section import Section
from training_provisioner.models.enrollment import Enrollment
import logging


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Load Canvas Training Courses"

    def handle(self, *args, **options):
        # Get active courses and sort by term_id to process earlier academic years first
        # This prevents race conditions when checking for previous enrollments
        active_courses = TrainingCourse.objects.active_courses().order_by('term_id')
        
        for training_course in active_courses:
            logger.info(
                "Loading training course "
                f"{training_course.blueprint_course_id} "
                f"for term {training_course.term_id}")

            logger.setLevel(logging.DEBUG)

            training_course.load_courses_and_enrollments()
