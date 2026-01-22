# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.core.management.base import BaseCommand
from django.core.management import call_command
from training_provisioner.models.training_course import TrainingCourse


class Command(BaseCommand):

    def handle(self, *args, **options):
        # clear the decks
        TrainingCourse.objects.all().delete()

        # seed data
        call_command('loaddata', 'test_data/training_course.json')
