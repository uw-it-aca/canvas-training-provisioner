# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from unittest.mock import patch, MagicMock, mock_open
import json
from django.test import TestCase
from training_provisioner.test import TrainingCourseTestCase
from training_provisioner.dao.membership import test_membership
from training_provisioner.models.training_course import TrainingCourse


class ZeroPaddingMembershipTest(TrainingCourseTestCase):
    """
    Test suite to verify that zero-padded user IDs from membership.json
    are properly preserved when loaded by the membership DAO.
    """

    def setUp(self):
        super().setUp()
        self.training_course = TrainingCourse.objects.get(pk=1)
        self.training_course.term_id = "AY2025-2026-101"

    @patch('training_provisioner.dao.membership.open', new_callable=mock_open)
    @patch('training_provisioner.dao.membership.mock_file_path')
    def test_membership_preserves_zero_padded_ids_from_json(self,
                                                            mock_path,
                                                            mock_file):
        """Test that membership loading preserves zero-padded IDs from JSON"""
        mock_path.return_value = "/fake/path/membership.json"

        # Test data with zero-padded ID (mimicking actual membership.json)
        test_membership_data = {
            "5432101": ["20254R", "20261A"],
            "0123456": ["20254R", "20261A"]  # Zero-padded test case
        }

        mock_file.return_value.read.return_value = json.dumps(
            test_membership_data)

        result = test_membership(self.training_course)

        # Verify zero-padded ID is preserved
        self.assertIn("0123456", result)
        self.assertNotIn("123456", result)  # Should NOT have stripped version

        # Verify the key is exactly as specified in JSON
        self.assertEqual(result["0123456"], ["20254R", "20261A"])

        # Verify all keys are strings
        for key in result.keys():
            self.assertIsInstance(key, str)

    @patch('training_provisioner.dao.membership.open', new_callable=mock_open)
    @patch('training_provisioner.dao.membership.mock_file_path')
    def test_membership_with_list_format_preserves_zero_padding(self,
                                                                mock_path,
                                                                mock_file):
        """Test that list format also preserves zero-padded IDs"""
        mock_path.return_value = "/fake/path/membership.json"

        # Test with list format (legacy format)
        test_membership_list = ["5432101", "0123456", "5432102"]

        mock_file.return_value.read.return_value = json.dumps(
            test_membership_list)

        result = test_membership(self.training_course)

        # Should convert list to dict but preserve zero-padding
        expected_result = {
            "5432101": ["20254R", "20261R"],
            "0123456": ["20254R", "20261R"],
            "5432102": ["20254R", "20261R"]
        }

        self.assertEqual(result, expected_result)

        # Specifically check zero-padded ID
        self.assertIn("0123456", result)
        self.assertIsInstance("0123456", str)

    def test_actual_membership_json_contains_zero_padded_id(self):
        """
        Test that our actual membership.json contains the zero-padded test ID
        """
        membership_data = self.get_membership()

        # Verify our test case is present in actual data
        self.assertIn("0123456", membership_data)

        # Verify it's a string key, not converted to int
        for key in membership_data.keys():
            self.assertIsInstance(key, str)
            if key.startswith('0'):
                self.assertTrue(len(key) >= 2)  # Ensure it's not just "0"

    def test_member_course_number_handles_zero_padded_id(self):
        """Test that member_course_number method handles zero-padded IDs"""
        # This tests the test infrastructure itself
        course_number = self.member_course_number("0123456")
        # Should return assigned course number
        self.assertEqual(course_number, 1)

        # Verify it doesn't work with the non-zero-padded version
        with self.assertRaises(KeyError):
            # Should NOT work without padding
            self.member_course_number("123456")
