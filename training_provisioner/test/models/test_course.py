# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.test import TestCase
from training_provisioner.models import (
    TrainingCourse, Course, ImportResource)


class CourseModelTest(TestCase):
    fixtures = ['test_data/training_course.json']

    def test_course_model(self):
        for training_course in TrainingCourse.objects.active_courses():
            Course.objects.add_courses(training_course)

        courses = Course.objects.all()
        self.assertEqual(courses.count(), 2)

        for course in courses:
            self.assertIsNotNone(course.training_course)
            self.assertEqual(course.priority, ImportResource.PRIORITY_DEFAULT)
