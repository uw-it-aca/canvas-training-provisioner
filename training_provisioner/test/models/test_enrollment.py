# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.test import TestCase
from training_provisioner.models import (
    TrainingCourse, Course, Enrollment, ImportResource)
from mock import patch


class EnrollmentModelTest(TestCase):
    fixtures = ['test_data/training_course.json']

    @patch('training_provisioner.models.'
           'training_course.get_title_vi_membership')
    def test_enrollment_model(self, mock_membership):
        mock_membership.return_value = ['12345678', '12345679']

        active_training_courses = TrainingCourse.objects.active_courses()
        for training_course in active_training_courses:
            Course.objects.add_courses(training_course)

        self.assertEqual(Course.objects.all().count(), 2)

        for training_course in active_training_courses:
            Enrollment.objects.add_enrollments(training_course)

        self.assertTrue(Enrollment.objects.all().count(), 2)
