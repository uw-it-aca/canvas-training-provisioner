# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.core.management.base import BaseCommand
from training_provisioner.models import (
    TrainingCourse, Term, Course, Section, Enrollment)
import logging


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Load Canvas Training Courses"

    def handle(self, *args, **options):
        for training_course in TrainingCourse.objects.active_courses():
            logger.info(
                "Loading training course "
                f"{training_course.blueprint_course_id} "
                f"for term {training_course.term_id}")

            Term.objects.add_term(training_course)
            Course.objects.add_courses(training_course)
            Section.objects.add_sections(training_course)
            Enrollment.objects.add_enrollments(training_course)
