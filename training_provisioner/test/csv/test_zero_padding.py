# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from training_provisioner.test import TrainingCourseTestCase
from training_provisioner.models.training_course import TrainingCourse
from training_provisioner.models.course import Course
from training_provisioner.models.section import Section
from training_provisioner.models.enrollment import Enrollment
from training_provisioner.csv.format import EnrollmentCSV
from mock import patch


class ZeroPaddingCSVTest(TrainingCourseTestCase):
    """
    Test suite to verify that zero-padded user IDs (like "0123456")
    are preserved throughout the CSV generation pipeline and not
    converted to integers that lose leading zeros.
    """

    @patch('training_provisioner.models.'
           'training_course.TrainingCourse.get_course_membership')
    def setUp(self, mock_membership):
        """Initialize with test data including zero-padded user ID"""
        mock_membership.return_value = self.get_membership()
        self.training_course = TrainingCourse.objects.active_courses()[0]
        Course.objects.add_models_for_training_course(self.training_course)
        Section.objects.add_models_for_training_course(self.training_course)
        Enrollment.objects.add_models_for_training_course(
            self.training_course)

    def test_csv_enrollment_preserves_zero_padding(self):
        """Test that EnrollmentCSV preserves zero-padded integration_ids"""
        # Find the enrollment with zero-padded ID
        zero_padded_enrollment = Enrollment.objects.get(
            integration_id="0123456")

        # Create CSV representation
        csv_enrollment = EnrollmentCSV(
            course_id=zero_padded_enrollment.course.course_id,
            integration_id=zero_padded_enrollment.integration_id,
            role='student',
            status='active'
        )

        # Convert to CSV string
        csv_line = str(csv_enrollment)

        # Verify zero-padded ID is preserved in CSV output
        self.assertIn("0123456", csv_line)
        self.assertNotIn("123456", csv_line.replace("0123456", ""))

        # Verify the integration_id field specifically
        self.assertEqual(zero_padded_enrollment.integration_id, "0123456")
        self.assertIsInstance(zero_padded_enrollment.integration_id, str)

    def test_all_enrollments_have_string_integration_ids(self):
        """
        Verify all enrollments have string integration_ids including
        zero-padded IDs
        """
        all_integration_ids = list(Enrollment.objects.values_list(
            'integration_id', flat=True))

        # Check that we have our zero-padded test case
        self.assertIn("0123456", all_integration_ids)

        # Verify all integration_ids are strings
        for integration_id in all_integration_ids:
            with self.subTest(integration_id=integration_id):
                self.assertIsInstance(integration_id, str)

                # If it starts with 0, ensure it's preserved
                if integration_id.startswith('0'):
                    self.assertTrue(len(integration_id) >= 2)
                    self.assertEqual(integration_id[0], '0')

    def test_csv_generation_with_mixed_id_formats(self):
        """
        Test CSV generation handles both regular and zero-padded IDs correctly
        """
        enrollments = Enrollment.objects.all()
        csv_lines = []

        for enrollment in enrollments:
            csv_enrollment = EnrollmentCSV(
                course_id=enrollment.course.course_id,
                integration_id=enrollment.integration_id,
                role='student',
                status='active'
            )
            csv_lines.append(str(csv_enrollment))

        # Find the line with zero-padded ID
        zero_padded_line = None
        for line in csv_lines:
            if "0123456" in line:
                zero_padded_line = line
                break

        self.assertIsNotNone(zero_padded_line,
                             "Zero-padded ID should appear in CSV output")

        # Verify it's formatted correctly and doesn't lose leading zero
        self.assertTrue(zero_padded_line.count("0123456") == 1,
                        "Zero-padded ID should appear exactly once per line")

        # Ensure no conversion to integer format happened
        self.assertNotIn(",123456,", zero_padded_line)
        self.assertIn(",0123456,", zero_padded_line)
