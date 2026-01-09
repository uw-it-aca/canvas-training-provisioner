# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

"""
Tests specifically for the reenrollment functionality in _add_enrollment.
"""
from unittest.mock import patch

from training_provisioner.models.training_course import TrainingCourse
from training_provisioner.models.enrollment import Enrollment
from training_provisioner.test import TrainingCourseTestCase


class ReenrollmentFunctionalityTest(TrainingCourseTestCase):
    """Test the reenrollment functionality added to _add_enrollment method."""

    def test_reenrollment_clears_deleted_date(self):
        """Test that reenrolling a previously deleted user clears the
        deleted_date."""
        # Set up course
        training_course = TrainingCourse.objects.get(pk=1)

        # Mock membership to return two users initially
        with patch('training_provisioner.models.training_course.'
                   'TrainingCourse.get_course_membership') as mock_membership:
            mock_membership.return_value = ['1001', '1002']

            # Initial enrollment of both users
            training_course.load_courses_and_enrollments()

            # Check that both enrollments were created
            enrollment1 = Enrollment.objects.get(integration_id='1001')
            enrollment2 = Enrollment.objects.get(integration_id='1002')
            self.assertIsNone(enrollment1.deleted_date)
            self.assertIsNone(enrollment2.deleted_date)

            # Mock to return only one user (1002 removed, but not empty list)
            mock_membership.return_value = ['1001']
            training_course.load_courses_and_enrollments()

            # Check that enrollment2 was marked as deleted
            enrollment1.refresh_from_db()
            enrollment2.refresh_from_db()
            self.assertIsNone(enrollment1.deleted_date)
            self.assertIsNotNone(enrollment2.deleted_date)

            # Mock to return both users again (1002 reenrollment)
            mock_membership.return_value = ['1001', '1002']

            # Capture logs to verify reenrollment message
            with self.assertLogs('training_provisioner.models.enrollment',
                                 level='INFO') as log:
                training_course.load_courses_and_enrollments()

                # Check that reenrollment was logged
                self.assertTrue(any('reactivate enrollment 1002' in
                                    message for message in log.output))

            # Check that enrollment2 deleted_date was cleared
            enrollment1.refresh_from_db()
            enrollment2.refresh_from_db()
            self.assertIsNone(enrollment1.deleted_date)
            self.assertIsNone(enrollment2.deleted_date)
            self.assertEqual(enrollment2.priority, Enrollment.PRIORITY_DEFAULT)

            # Verify only one enrollment record exists (not multiple)
            enrollments = Enrollment.objects.filter(integration_id='1001')
            self.assertEqual(enrollments.count(), 1)
