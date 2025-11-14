# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.test import TestCase
import json
import os


class TrainingCourseTestCase(TestCase):
    fixtures = ['test_data/training_course.json']

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
        }[member]
