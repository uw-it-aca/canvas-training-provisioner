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
            '5432101': 7,
            '5432102': 8,
            '5432103': 9,
            '5432104': 2,
            '5432105': 3,
            '5432106': 4,
            '5432107': 5,
            '5432108': 6,
            '5432109': 7,
            '5432110': 8,
        }[member]
