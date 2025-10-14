# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.core.management.base import BaseCommand
from training_provisioner.models.training_course import TrainingCourse
from training_provisioner.models import (Term, Course, Section, Enrollment)


class Command(BaseCommand):
    help = "Load Canvas Training Courses"

    def add_arguments(self, parser):
        parser.add_argument('term_id', type=str,
            help='Load training courses for the given term (e.g., 2024-2025)')

    def handle(self, *args, **options):
        term_id = options.get('term_id')

        for training_course in TrainingCourse.objects.active_courses():
            Term.objects.add_term(training_course.term_id)
            Course.objects.add_courses(training_course)
            Section.objects.add_sections(training_course)
            Enrollment.objects.add_enrollments(training_course)
