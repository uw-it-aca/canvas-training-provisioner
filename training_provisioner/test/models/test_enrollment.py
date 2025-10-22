# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from training_provisioner.test import TrainingCourseTestCase
from training_provisioner.models import (
    TrainingCourse, Course, Enrollment, ImportResource)
from training_provisioner.exceptions import EnrollmentCourseMismatch
from mock import patch


class EnrollmentModelTest(TrainingCourseTestCase):
    @patch('training_provisioner.models.'
           'training_course.get_title_vi_membership')
    def test_enrollment_model(self, mock_membership):
        mock_membership.return_value = self.get_membership()
        course_id_prefix = None

        active_training_courses = TrainingCourse.objects.active_courses()
        for training_course in active_training_courses:
            Enrollment.objects.add_enrollments(training_course)
            course_count = training_course.course_count
            course_id_prefix = training_course.course_id_prefix

        self.assertTrue(
            Enrollment.objects.all().count(),
            len(mock_membership.return_value))

        for i, member in enumerate(mock_membership.return_value):
            enrollment = Enrollment.objects.get(integration_id=member)
            self.assertEqual(
                enrollment.course_id,
                f"{course_id_prefix}"
                f"{self.member_course_number(member)}")

    @patch('training_provisioner.models.'
           'training_course.get_title_vi_membership')
    def test_enrollment_model_delete(self, mock_membership):
        mock_membership.return_value = self.get_membership()
        integration_id_to_delete = '5432199'
        enrollment = Enrollment.objects.create(
            course_id='AY2025-2026-BLUEPRINT_123-2',
            integration_id=integration_id_to_delete,
            priority=ImportResource.PRIORITY_DEFAULT)

        active_training_courses = TrainingCourse.objects.active_courses()
        for training_course in active_training_courses:
            Enrollment.objects.add_enrollments(training_course)

        enrollment = Enrollment.objects.get(
            integration_id=integration_id_to_delete)
        self.assertIsNotNone(enrollment.deleted_date)

    def test_enrollment_change_error(self):
        integration_id = '5432101'
        training_course = TrainingCourse.objects.active_courses()[0]

        enrollment = Enrollment.objects.create(
            course_id=f"{training_course.course_id_prefix}999",
            integration_id=integration_id,
            priority=ImportResource.PRIORITY_DEFAULT)

        with self.assertRaises(EnrollmentCourseMismatch):
            Enrollment.objects._add_enrollment(
                integration_id, training_course)
