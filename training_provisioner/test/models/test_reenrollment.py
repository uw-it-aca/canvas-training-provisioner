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

        # Mock membership to return one user
        with patch('training_provisioner.models.training_course.'
                   'TrainingCourse.get_course_membership') as mock_membership:
            mock_membership.return_value = ['1001']

            # Initial enrollment
            training_course.load_courses_and_enrollments()

            # Check that enrollment was created
            enrollment = Enrollment.objects.get(integration_id='1001')
            self.assertIsNone(enrollment.deleted_date)
            self.assertEqual(enrollment.priority, Enrollment.PRIORITY_DEFAULT)

            # Mock to return empty list (user removed)
            mock_membership.return_value = []
            training_course.load_courses_and_enrollments()

            # Check that enrollment was marked as deleted
            enrollment.refresh_from_db()
            self.assertIsNotNone(enrollment.deleted_date)

            # Mock to return the user again (reenrollment)
            mock_membership.return_value = ['1001']

            # Capture logs to verify reenrollment message
            with self.assertLogs('training_provisioner.models.enrollment',
                                 level='INFO') as log:
                training_course.load_courses_and_enrollments()

                # Check that reenrollment was logged
                self.assertTrue(any('reactivate enrollment 1001' in
                                    message for message in log.output))

            # Check that enrollment deleted_date was cleared
            enrollment.refresh_from_db()
            self.assertIsNone(enrollment.deleted_date)
            self.assertEqual(enrollment.priority, Enrollment.PRIORITY_DEFAULT)

            # Verify only one enrollment record exists (not multiple)
            enrollments = Enrollment.objects.filter(integration_id='1001')
            self.assertEqual(enrollments.count(), 1)
