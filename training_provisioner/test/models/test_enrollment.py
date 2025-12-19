# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from training_provisioner.test import TrainingCourseTestCase
from training_provisioner.models import ImportResource
from training_provisioner.models.training_course import TrainingCourse
from training_provisioner.models.course import Course
from training_provisioner.models.section import Section
from training_provisioner.models.enrollment import Enrollment
from training_provisioner.exceptions import EnrollmentCourseMismatch
from mock import patch


class EnrollmentModelTest(TrainingCourseTestCase):
    @patch('training_provisioner.models.'
           'training_course.TrainingCourse.get_course_membership')
    def setUp(self, mock_membership):
        """
        initialize db for mock membership
        """
        mock_membership.return_value = self.get_membership()
        self.training_course = TrainingCourse.objects.get(pk=1)

        Course.objects.add_models_for_training_course(self.training_course)
        Section.objects.add_models_for_training_course(self.training_course)
        Enrollment.objects.add_models_for_training_course(self.training_course)

    def test_enrollment_model(self):
        self.assertTrue(
            Enrollment.objects.all().count(),
            len(self.get_membership()))

        for i, member in enumerate(self.get_membership()):
            enrollment = Enrollment.objects.get(integration_id=member)
            self.assertEqual(
                enrollment.course.course_id,
                (f"{self.training_course.course_id_prefix}"
                 f"{self.member_course_number(member):03d}"))

    def test_enrollment_model_delete(self):
        integration_id_to_delete = '5432199'

        enrollment_three = Enrollment.objects.get(pk=3)
        enrollment = Enrollment.objects.create(
            course=enrollment_three.course,
            integration_id=integration_id_to_delete)

        Enrollment.objects.add_models_for_training_course(self.training_course)

        enrollment = Enrollment.objects.get(
            integration_id=integration_id_to_delete)
        self.assertIsNotNone(enrollment.deleted_date)

    @patch('training_provisioner.models.'
           'training_course.TrainingCourse.get_course_membership')
    def test_enrollment_addition(self, mock_membership):
        Course.objects.update(priority=Course.PRIORITY_NONE)
        Section.objects.update(priority=Section.PRIORITY_NONE)
        Enrollment.objects.update(priority=Enrollment.PRIORITY_NONE)

        student_number = '5432123'
        mock_membership.return_value = self.get_membership() + [student_number]

        Enrollment.objects.add_models_for_training_course(self.training_course)

        self.assertEqual(Course.objects.filter(priority__gt=0).count(), 1)

        enrollments = Enrollment.objects.filter(priority__gt=0)
        self.assertEqual(enrollments.count(), 1)

        enrollment = enrollments[0]
        self.assertTrue(enrollment.priority > Enrollment.PRIORITY_NONE)
        self.assertEqual(enrollment.integration_id, student_number)
        self.assertTrue(enrollment.is_active)

    @patch('training_provisioner.models.'
           'training_course.TrainingCourse.get_course_membership')
    def test_enrollment_removal(self, mock_membership):
        Course.objects.update(priority=Course.PRIORITY_NONE)
        Section.objects.update(priority=Section.PRIORITY_NONE)
        Enrollment.objects.update(priority=Enrollment.PRIORITY_NONE)

        membership = self.get_membership()
        student_number = membership[2]
        del membership[2]

        mock_membership.return_value = membership

        Enrollment.objects.add_models_for_training_course(self.training_course)

        self.assertEqual(Course.objects.filter(priority__gt=0).count(), 1)

        enrollments = Enrollment.objects.filter(priority__gt=0)
        self.assertEqual(enrollments.count(), 1)

        enrollment = enrollments[0]
        self.assertEqual(enrollment.integration_id, student_number)
        self.assertFalse(enrollment.is_active)

    def test_enrollment_course_change(self):
        integration_id = '5432101'

        enrollment = Enrollment.objects.get(
            integration_id=integration_id)

        # course that _add_enrollment will assign to enrollment
        new_course = enrollment.course

        # change enrollment to "old" course
        enrollment_six = Enrollment.objects.get(pk=6)
        old_course = enrollment_six.course
        enrollment.course = old_course
        enrollment.save()

        with self.assertRaises(EnrollmentCourseMismatch):
            Enrollment.objects._add_enrollment(
                integration_id, self.training_course)

    def test_enrollment_section_change(self):
        training_course = TrainingCourse.objects.get(pk=2)

        # bump term for booster course enrollments
        training_course.term_id = 'AY2026-2027'
        Course.objects.add_models_for_training_course(training_course)
        Section.objects.add_models_for_training_course(training_course)
        Enrollment.objects.add_models_for_training_course(training_course)

        integration_id = '5432101'

        enrollment = Enrollment.objects.get(
            course__training_course=training_course,
            integration_id=integration_id)

        # section that _add_enrollment will assign to enrollment
        new_section = enrollment.section

        # change enrollment to "old" section
        old_section = None
        for section_id in enrollment.course.section_import_ids:
            if section_id != new_section.section_id:
                old_section = Section.objects.get(section_id=section_id)
                enrollment.section = old_section
                enrollment.save()
                break

        self.skipTest("no alternate section found for course "
                      f" {enrollment.course.course_id}")

        Enrollment.objects._add_enrollment(integration_id, training_course)

        enrollments = Enrollment.objects.filter(
            course__training_course=training_course,
            integration_id=integration_id)

        self.assertEqual(enrollments.count(), 2)
        self.assertTrue(enrollments[0].priority > Enrollment.PRIORITY_NONE)
        self.assertTrue(enrollments[1].priority > Enrollment.PRIORITY_NONE)

        self.assertIsNotNone(
            enrollments[0].deleted_date if (
                enrollments[0].section == old_section) else
            enrollments[1].deleted_date)
        self.assertIsNone(
            enrollments[0].deleted_date if (
                enrollments[0].section == new_section) else
            enrollments[1].deleted_date)
