# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from training_provisioner.test import TrainingCourseTestCase
from training_provisioner.models import (
    TrainingCourse, Course, ImportResource)


class CourseModelTest(TrainingCourseTestCase):
    def test_course_model(self):
        for training_course in TrainingCourse.objects.active_courses():
            Course.objects.add_courses(training_course)

        courses = Course.objects.all()
        self.assertEqual(courses.count(), 8)

        for course in courses:
            self.assertIsNotNone(course.training_course)
            self.assertEqual(course.priority, ImportResource.PRIORITY_DEFAULT)
