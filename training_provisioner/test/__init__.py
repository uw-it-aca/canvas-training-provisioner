# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.test import TestCase
from django.core.management import call_command
from io import StringIO
import json
import os


class TrainingCourseTestCase(TestCase):
    fixtures = ['test_data/training_course.json']

    def call_load_training_courses(self):
        return self._call_command('load_training_courses')

    def call_import_training_courses(self):
        return self._call_command('import_training_courses')

    def _call_command(self, command_name, *args, **kwargs):
        out = StringIO()
        call_command(command_name,
                     *args,
                     stdout=out,
                     stderr=StringIO(),
                     **kwargs)
        return out.getvalue()

    def get_membership(self):
        membership_file = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__), '../data/membership.json'))
        with open(membership_file) as f:
            return json.load(f)

    def member_course_number(self, member):
        return {
            '5432101': 6,
            '5432102': 7,
            '5432103': 8,
            '5432104': 1,
            '5432105': 2,
            '5432106': 3,
            '5432107': 4,
            '5432108': 5,
            '5432109': 6,
            '5432110': 7,
            '0123456': 1
        }[member]
