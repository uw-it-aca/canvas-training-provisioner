# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.test import TestCase
from training_provisioner.models import Course


class CourseModelTest(TestCase):
    fixtures = ['test_data/training_course.json', 'test_data/course.json']

    def test_course_model(self):
        course = Course.objects.all()[0]
        self.assertEqual(course.training_course.pk, 1)
        self.assertEqual(course.priority, Course.PRIORITY_DEFAULT)
        self.assertIsNone(course.queue_id)
        self.assertIsNone(course.deleted_date)

