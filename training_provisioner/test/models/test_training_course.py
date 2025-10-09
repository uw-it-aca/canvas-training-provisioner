# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.test import TestCase
from training_provisioner.models import TrainingCourse
import mock


class TrainingCourseModelTest(TestCase):
    fixtures = ['test_data/training_course.json']

    @mock.patch(
        'training_provisioner.dao.membership.get_title_vi_membership',
        return_value=['12345678', '12345677'])
    def test_membership(self, mock_update):

        courses = TrainingCourse.objects.active_courses()

        self.assertEqual(courses.count(), 1)
