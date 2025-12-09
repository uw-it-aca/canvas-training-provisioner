# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from unittest.mock import patch, MagicMock, mock_open
import pandas as pd
import json
from django.test import TestCase, override_settings
from training_provisioner.test import TrainingCourseTestCase
from training_provisioner.dao.membership import (
    test_membership,
    title_vi_membership_candidates,
    title_vi_booster_membership_candidates,
    get_quarters_in_ay,
    get_current_quarter_info,
    get_info_for_quarter,
    get_students_from_registration,
    get_students_from_admissions
)
from training_provisioner.models.training_course import TrainingCourse


class MembershipDAOTest(TrainingCourseTestCase):

    def setUp(self):
        super().setUp()
        self.training_course = TrainingCourse.objects.get(pk=1)
        self.training_course.term_id = "AY2025-2026-101"

    @patch('training_provisioner.dao.membership.open', new_callable=mock_open)
    @patch('training_provisioner.dao.membership.mock_file_path')
    def test_test_membership_success(self, mock_path, mock_file):
        """Test test_membership function with successful JSON loading."""
        mock_path.return_value = "/fake/path/membership.json"
        mock_data = ["student1", "student2", "student3"]
        mock_file.return_value.read.return_value = json.dumps(mock_data)

        result = test_membership(self.training_course)

        self.assertEqual(result, mock_data)
        mock_path.assert_called_once_with("membership.json")

    @patch('training_provisioner.dao.membership.open',
           side_effect=FileNotFoundError())
    @patch('training_provisioner.dao.membership.mock_file_path')
    @patch('training_provisioner.dao.membership.logger')
    def test_test_membership_file_error(self,
                                        mock_logger,
                                        mock_path,
                                        mock_file):
        """Test test_membership function with file error."""
        mock_path.return_value = "/fake/path/membership.json"

        result = test_membership(self.training_course)

        self.assertEqual(result, [])
        mock_logger.error.assert_called_once()

    def test_get_quarters_in_ay_valid_format(self):
        """Test get_quarters_in_ay with valid academic year format."""
        result = get_quarters_in_ay("2025/2026", None)
        expected = ["20253", "20254", "20261", "20262"]

        self.assertEqual(result, expected)

    def test_get_quarters_in_ay_invalid_format(self):
        """Test get_quarters_in_ay with invalid academic year format."""
        with self.assertRaises(ValueError) as context:
            get_quarters_in_ay("2025-2026", None)

        self.assertIn("Invalid academic_year format", str(context.exception))

        with self.assertRaises(ValueError) as context:
            get_quarters_in_ay("25/26", None)

        self.assertIn("Invalid academic_year format", str(context.exception))

    def test_get_quarters_in_ay_with_current_quarter(self):
        """Test get_quarters_in_ay with current quarter specified."""
        # Test quarter in middle of AY
        result = get_quarters_in_ay("2025/2026", "20254")
        expected = ["20254", "20261", "20262"]
        self.assertEqual(result, expected)

        # Test first quarter of AY
        result = get_quarters_in_ay("2025/2026", "20253")
        expected = ["20253", "20254", "20261", "20262"]
        self.assertEqual(result, expected)

        # Test last quarter of AY
        result = get_quarters_in_ay("2025/2026", "20262")
        expected = ["20262"]
        self.assertEqual(result, expected)

    def test_get_quarters_in_ay_quarter_before_ay(self):
        """Test get_quarters_in_ay with quarter before academic year."""
        # Quarter before AY starts
        result = get_quarters_in_ay("2025/2026", "20241")
        expected = ["20253", "20254", "20261", "20262"]

        self.assertEqual(result, expected)

    def test_get_quarters_in_ay_quarter_after_ay(self):
        """Test get_quarters_in_ay with quarter after academic year."""
        # Quarter after AY ends
        result = get_quarters_in_ay("2025/2026", "20271")
        expected = []

        self.assertEqual(result, expected)

    def test_get_quarters_in_ay_string_quarter(self):
        """Test get_quarters_in_ay with string quarter code."""
        result = get_quarters_in_ay("2025/2026", "20254")
        expected = ["20254", "20261", "20262"]

        self.assertEqual(result, expected)

    @patch('training_provisioner.dao.membership.execute_edw_query')
    def test_get_current_quarter_info(self, mock_query):
        """Test get_current_quarter_info function."""
        mock_df = pd.DataFrame([{
            'AcademicContigYrQtrCode': 20254,
            'AcademicYrName': '2025/2026',
            'CensusDayStatus': 'After Census Day'
        }])
        mock_query.return_value = mock_df

        result = get_current_quarter_info()

        expected = {
            'AcademicContigYrQtrCode': 20254,
            'AcademicYrName': '2025/2026',
            'CensusDayStatus': 'After Census Day'
        }
        self.assertEqual(result, expected)

        # Verify SQL query contains expected elements
        call_args = mock_query.call_args[0][0]
        self.assertIn('dimDate', call_args)
        self.assertIn('AcademicContigYrQtrCode', call_args)
        self.assertIn('CensusDayStatus', call_args)
        self.assertIn('GETDATE()', call_args)

    @patch('training_provisioner.dao.membership.execute_edw_query')
    def test_get_info_for_quarter_valid(self, mock_query):
        """Test get_info_for_quarter with valid quarter code."""
        mock_df = pd.DataFrame([{
            'AcademicContigYrQtrCode': 20254,
            'AcademicYrName': '2025/2026',
            'CensusDayStatus': 'Before Census Day'
        }])
        mock_query.return_value = mock_df

        result = get_info_for_quarter("20254")

        expected = {
            'AcademicContigYrQtrCode': 20254,
            'AcademicYrName': '2025/2026',
            'CensusDayStatus': 'Before Census Day'
        }
        self.assertEqual(result, expected)

        # Verify SQL query contains quarter code
        call_args = mock_query.call_args[0][0]
        self.assertIn('20254', call_args)

    def test_get_info_for_quarter_invalid_format(self):
        """Test get_info_for_quarter with invalid quarter code format."""
        with self.assertRaises(ValueError) as context:
            get_info_for_quarter("2025")

        self.assertIn("Invalid quarter_code format", str(context.exception))

        with self.assertRaises(ValueError) as context:
            get_info_for_quarter("abc123")

        self.assertIn("Invalid quarter_code format", str(context.exception))

    def test_get_info_for_quarter_integer_input(self):
        """Test get_info_for_quarter with integer input."""
        with patch('training_provisioner.dao.membership.execute_edw_query') \
                as mock_query:
            mock_df = pd.DataFrame([{
                'AcademicContigYrQtrCode': 20254,
                'AcademicYrName': '2025/2026',
                'CensusDayStatus': 'After Census Day'
            }])
            mock_query.return_value = mock_df

            result = get_info_for_quarter(20254)

            # Should work with integer input
            self.assertIn('AcademicContigYrQtrCode', result)
            call_args = mock_query.call_args[0][0]
            self.assertIn('20254', call_args)

    @patch('training_provisioner.dao.membership.execute_edw_query')
    def test_get_students_from_registration_valid(self, mock_query):
        """Test get_students_from_registration with valid quarter code."""
        mock_df = pd.DataFrame([
            {'StudentNumber': 1234567},
            {'StudentNumber': 2345678},
            {'StudentNumber': 3456789}
        ])
        mock_query.return_value = mock_df

        result = get_students_from_registration("20254")

        expected = [1234567, 2345678, 3456789]
        self.assertEqual(result, expected)

        # Verify SQL query elements
        call_args = mock_query.call_args[0][0]
        self.assertIn('registration', call_args)
        self.assertIn('student_1', call_args)
        self.assertIn('20254', call_args)
        self.assertIn('enroll_status = 12', call_args)

    def test_get_students_from_registration_invalid_format(self):
        """Test get_students_from_registration with invalid quarter code."""
        with self.assertRaises(ValueError) as context:
            get_students_from_registration("2025")

        self.assertIn("Invalid quarter_code format", str(context.exception))

    @patch('training_provisioner.dao.membership.execute_edw_query')
    def test_get_students_from_registration_integer_input(self, mock_query):
        """Test get_students_from_registration with integer input."""
        mock_df = pd.DataFrame([{'StudentNumber': 1234567}])
        mock_query.return_value = mock_df

        result = get_students_from_registration(20254)

        self.assertEqual(result, [1234567])

    @patch('training_provisioner.dao.membership.execute_edw_query')
    def test_get_students_from_admissions_valid(self, mock_query):
        """Test get_students_from_admissions with valid quarter code."""
        mock_df = pd.DataFrame([
            {'StudentNumber': 9876543},
            {'StudentNumber': 8765432}
        ])
        mock_query.return_value = mock_df

        result = get_students_from_admissions("20254")

        expected = [9876543, 8765432]
        self.assertEqual(result, expected)

        # Verify SQL query elements
        call_args = mock_query.call_args[0][0]
        self.assertIn('student_1', call_args)
        self.assertIn('sr_adm_appl', call_args)
        self.assertIn('20254', call_args)
        self.assertIn('appl_status IN (15, 16)', call_args)

    def test_get_students_from_admissions_invalid_format(self):
        """Test get_students_from_admissions with invalid quarter code."""
        with self.assertRaises(ValueError) as context:
            get_students_from_admissions("invalid")

        self.assertIn("Invalid quarter_code format", str(context.exception))

    @patch('training_provisioner.dao.membership.execute_edw_query')
    def test_get_students_from_admissions_integer_input(self, mock_query):
        """Test get_students_from_admissions with integer input."""
        mock_df = pd.DataFrame([{'StudentNumber': 9876543}])
        mock_query.return_value = mock_df

        result = get_students_from_admissions(20254)

        self.assertEqual(result, [9876543])


class TitleVIMembershipTest(TrainingCourseTestCase):

    def setUp(self):
        super().setUp()
        self.training_course = TrainingCourse.objects.get(pk=1)
        self.training_course.term_id = "AY2025-2026"

    def test_title_vi_membership_invalid_term_format(self):
        """Test title_vi_membership_candidates with invalid term format."""
        self.training_course.term_id = "2025-2026"

        with self.assertRaises(ValueError) as context:
            title_vi_membership_candidates(self.training_course)

        self.assertIn("Invalid term_id format", str(context.exception))

    @patch('training_provisioner.dao.membership.get_students_from_registration'
           )
    @patch('training_provisioner.dao.membership.get_students_from_admissions')
    @patch('training_provisioner.dao.membership.get_info_for_quarter')
    @patch('training_provisioner.dao.membership.get_quarters_in_ay')
    def test_title_vi_membership_ay_2025_2026_special_case(self, mock_quarters,
                                                           mock_quarter_info,
                                                           mock_admissions,
                                                           mock_registration):
        """
        Test title_vi_membership_candidates for AY2025-2026 special case
        (Spring 2026 only).
        """
        self.training_course.term_id = "AY2025-2026"

        # Mock the quarters function to be called with Spring 2026 start
        mock_quarters.return_value = ["20262"]  # Spring 2026 only
        mock_quarter_info.return_value = {
            'CensusDayStatus': 'Before Census Day'
            }
        mock_registration.return_value = [1111111, 2222222]
        mock_admissions.return_value = [3333333, 4444444]

        result = title_vi_membership_candidates(self.training_course)

        # Should get students from both registration and admissions
        # in Spring 2026
        expected = [1111111, 2222222, 3333333, 4444444]
        self.assertEqual(sorted(result), sorted(expected))

        # Verify get_quarters_in_ay was called with Spring 2026 start
        mock_quarters.assert_called_once_with("2025/2026", 20262)

    @patch('training_provisioner.dao.membership.get_students_from_registration'
           )
    @patch('training_provisioner.dao.membership.get_students_from_admissions')
    @patch('training_provisioner.dao.membership.get_info_for_quarter')
    @patch('training_provisioner.dao.membership.get_quarters_in_ay')
    def test_title_vi_membership_normal_ay(self,
                                           mock_quarters,
                                           mock_quarter_info,
                                           mock_admissions,
                                           mock_registration):
        """Test title_vi_membership_candidates for normal academic year."""
        self.training_course.term_id = "AY2026-2027"

        # Mock normal AY with multiple quarters
        mock_quarters.return_value = ["20263", "20264", "20271", "20272"]
        mock_quarter_info.side_effect = [
            {'CensusDayStatus': 'After Census Day'},   # Summer 2026
            {'CensusDayStatus': 'Before Census Day'},  # Autumn 2026
            {'CensusDayStatus': 'After Census Day'},   # Winter 2027
            {'CensusDayStatus': 'Before Census Day'}   # Spring 2027
        ]

        # Mock different students for each quarter
        mock_registration.side_effect = [
            [1001, 1002],  # Summer
            [2001, 2002],  # Autumn
            [3001, 3002],  # Winter
            [4001, 4002]   # Spring
        ]
        # Admissions is only called for 'Before Census Day' quarters
        # (Autumn and Spring)
        mock_admissions.side_effect = [
            [5001, 5002],  # Autumn (before census)
            [6001, 6002]   # Spring (before census)
        ]

        result = title_vi_membership_candidates(self.training_course)

        # Should get all registration students plus admissions for
        # before-census quarters only
        expected = [1001, 1002, 2001, 2002, 3001, 3002, 4001, 4002,
                    5001, 5002, 6001, 6002]
        self.assertEqual(sorted(result), sorted(expected))

        # Verify get_quarters_in_ay was called without start quarter
        mock_quarters.assert_called_once_with("2026/2027", None)

        # Verify admissions was called exactly twice
        # (for before census quarters only)
        self.assertEqual(mock_admissions.call_count, 2)

    @patch('training_provisioner.dao.membership.get_students_from_registration'
           )
    @patch('training_provisioner.dao.membership.get_students_from_admissions')
    @patch('training_provisioner.dao.membership.get_info_for_quarter')
    @patch('training_provisioner.dao.membership.get_quarters_in_ay')
    def test_title_vi_membership_duplicate_students(self,
                                                    mock_quarters,
                                                    mock_quarter_info,
                                                    mock_admissions,
                                                    mock_registration):
        """
        Test title_vi_membership_candidates with duplicate students across
        quarters.
        """
        self.training_course.term_id = "AY2026-2027"

        mock_quarters.return_value = ["20271", "20272"]
        mock_quarter_info.side_effect = [
            {'CensusDayStatus': 'Before Census Day'},  # Winter
            {'CensusDayStatus': 'Before Census Day'}   # Spring
        ]

        # Same students appear in multiple quarters
        mock_registration.side_effect = [
            [1001, 1002, 1003],  # Winter
            [1002, 1003, 1004]   # Spring (1002, 1003 are duplicates)
        ]
        mock_admissions.side_effect = [
            [1003, 2001],  # Winter (1003 is duplicate from registration)
            [2001, 2002]   # Spring (2001 is duplicate from previous quarter)
        ]

        result = title_vi_membership_candidates(self.training_course)

        # Should deduplicate - each student should appear only once
        expected = [1001, 1002, 1003, 1004, 2001, 2002]
        self.assertEqual(sorted(result), sorted(expected))

    def test_title_vi_booster_membership_candidates(self):
        """
        Test title_vi_booster_membership_candidates delegates to main function.
        """
        with patch('training_provisioner.dao.membership.'
                   'title_vi_membership_candidates') as mock_main:
            mock_main.return_value = [1234, 5678]

            result = title_vi_booster_membership_candidates(
                self.training_course)

            self.assertEqual(result, [1234, 5678])
            mock_main.assert_called_once_with(self.training_course)


class MembershipIntegrationTest(TrainingCourseTestCase):
    """Integration tests that combine multiple membership functions."""

    def setUp(self):
        super().setUp()
        self.training_course = TrainingCourse.objects.get(pk=1)
        self.training_course.term_id = "AY2025-2026"

    @patch('training_provisioner.dao.membership.execute_edw_query')
    def test_end_to_end_membership_flow(self, mock_query):
        """Test a complete end-to-end membership determination flow."""
        # Mock EDW responses for different function calls based on query resp
        def mock_query_side_effect(query):
            if 'GETDATE()' in query and \
                    'CalendarDate = CONVERT(DATE, GETDATE())' in query:
                # get_current_quarter_info
                return pd.DataFrame([{
                    'AcademicContigYrQtrCode': 20262,
                    'AcademicYrName': '2025/2026',
                    'CensusDayStatus': 'Before Census Day'
                }])
            elif 'AcademicQtrCensusDayInd = \'Y\'' in query:
                # get_info_for_quarter
                return pd.DataFrame([{
                    'AcademicContigYrQtrCode': 20262,
                    'AcademicYrName': '2025/2026',
                    'CensusDayStatus': 'Before Census Day'
                }])
            elif 'registration' in query:
                # get_students_from_registration
                return pd.DataFrame([
                    {'StudentNumber': 1111111},
                    {'StudentNumber': 2222222}
                ])
            elif 'sr_adm_appl' in query:
                # get_students_from_admissions
                return pd.DataFrame([
                    {'StudentNumber': 3333333},
                    {'StudentNumber': 4444444}
                ])
            else:
                return pd.DataFrame()

        mock_query.side_effect = mock_query_side_effect

        # Test the full flow
        current_quarter = get_current_quarter_info()
        self.assertEqual(current_quarter['AcademicContigYrQtrCode'], 20262)

        quarter_info = get_info_for_quarter(20262)
        self.assertEqual(quarter_info['CensusDayStatus'], 'Before Census Day')

        registration_students = get_students_from_registration(20262)
        self.assertEqual(registration_students, [1111111, 2222222])

        admission_students = get_students_from_admissions(20262)
        self.assertEqual(admission_students, [3333333, 4444444])

        # Mock get_quarters_in_ay separately since it doesn't use EDW
        with patch('training_provisioner.dao.membership.get_quarters_in_ay') \
                as mock_quarters:
            mock_quarters.return_value = ["20262"]

            # Test the main membership function
            result = title_vi_membership_candidates(self.training_course)
            expected = [1111111, 2222222, 3333333, 4444444]
            self.assertEqual(sorted(result), sorted(expected))
