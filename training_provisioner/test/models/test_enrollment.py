# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from training_provisioner.test import TrainingCourseTestCase
from training_provisioner.models import (
    TrainingCourse, Course, Section, Enrollment, ImportResource)
from training_provisioner.exceptions import EnrollmentCourseMismatch
from mock import patch


class EnrollmentModelTest(TrainingCourseTestCase):
    @patch('training_provisioner.models.'
           'training_course.get_title_vi_membership')
    def setUp(self, mock_membership):
        """
        initialize db for mock membership
        """
        mock_membership.return_value = self.get_membership()
        self.training_course = TrainingCourse.objects.active_courses()[0]
        Course.objects.add_courses(self.training_course)
        Section.objects.add_sections(self.training_course)
        Enrollment.objects.add_enrollments(self.training_course)

    def test_enrollment_model(self):
        self.assertTrue(
            Enrollment.objects.all().count(),
            len(self.get_membership()))

        for i, member in enumerate(self.get_membership()):
            enrollment = Enrollment.objects.get(integration_id=member)
            self.assertEqual(
                enrollment.course.course_id,
                (f"{self.training_course.course_id_prefix}"
                 f"{self.member_course_number(member)}"))

    def test_enrollment_model_delete(self):
        integration_id_to_delete = '5432199'

        enrollment_three = Enrollment.objects.get(pk=3)
        enrollment = Enrollment.objects.create(
            course=enrollment_three.course,
            integration_id=integration_id_to_delete)

        Enrollment.objects.add_enrollments(self.training_course)

        enrollment = Enrollment.objects.get(
            integration_id=integration_id_to_delete)
        self.assertIsNotNone(enrollment.deleted_date)

    def test_enrollment_change_error(self):
        integration_id = '5432101'

        enrollment = Enrollment.objects.get(
            integration_id=integration_id)
        enrollment_six = Enrollment.objects.get(pk=6)

        enrollment.course = enrollment_six.course
        enrollment.save()

        with self.assertRaises(EnrollmentCourseMismatch):
            Enrollment.objects._add_enrollment(
                integration_id, self.training_course)
