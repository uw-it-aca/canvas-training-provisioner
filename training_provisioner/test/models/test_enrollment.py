# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.test import TestCase
from training_provisioner.models import (
    TrainingCourse, Course, Enrollment, ImportResource)
from training_provisioner.exceptions import EnrollmentCourseMismatch
from mock import patch


class EnrollmentModelTest(TestCase):
    fixtures = ['test_data/training_course.json']

    @patch('training_provisioner.models.'
           'training_course.get_title_vi_membership')
    def test_enrollment_model(self, mock_membership):
        mock_membership.return_value = ['12345678', '12345679']

        active_training_courses = TrainingCourse.objects.active_courses()
        for training_course in active_training_courses:
            Enrollment.objects.add_enrollments(training_course)

        self.assertTrue(Enrollment.objects.all().count(), 2)

        enrollment = Enrollment.objects.get(integration_id='12345678')
        self.assertEqual(enrollment.course_id, 'BLUEPRINT_123-2025-2026-0')

        enrollment = Enrollment.objects.get(integration_id='12345679')
        self.assertEqual(enrollment.course_id, 'BLUEPRINT_123-2025-2026-1')

    def test_enrollment_change_error(self):
        enrollment = Enrollment.objects.create(
            course_id='BLUEPRINT_123-2025-2026-1',
            integration_id='12345678',
            priority=ImportResource.PRIORITY_DEFAULT)

        active_training_courses = TrainingCourse.objects.active_courses()

        with self.assertRaises(EnrollmentCourseMismatch):
            Enrollment.objects._add_enrollment(
                '12345678', active_training_courses[0])
