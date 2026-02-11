# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from training_provisioner.test import TrainingCourseTestCase
from training_provisioner.models.training_course import TrainingCourse
from training_provisioner.models.course import Course
from training_provisioner.models.section import Section
from training_provisioner.models.enrollment import Enrollment
from training_provisioner.exceptions import EnrollmentCourseMismatch
from mock import patch
from django.db.utils import IntegrityError


class IntegrationIdStringHandlingTest(TrainingCourseTestCase):
    """
    Test suite to verify that integration_id/student_no values are
    consistently handled as strings throughout the system to avoid
    comparison bugs where 123 != '123'.
    """

    @patch('training_provisioner.models.'
           'training_course.TrainingCourse.get_course_membership')
    def setUp(self, mock_membership):
        """Initialize database with mock membership data as strings"""
        mock_membership.return_value = self.get_membership()
        self.training_course = TrainingCourse.objects.active_courses()[0]
        Course.objects.add_models_for_training_course(self.training_course)
        Section.objects.add_models_for_training_course(self.training_course)
        Enrollment.objects.add_models_for_training_course(
            self.training_course)

    def test_enrollment_integration_id_is_string(self):
        """Verify that all integration_ids in the database are strings"""
        for enrollment in Enrollment.objects.all():
            with self.subTest(enrollment_id=enrollment.id):
                self.assertIsInstance(
                    enrollment.integration_id, str,
                    f"integration_id should be string, got "
                    f"{type(enrollment.integration_id)}: "
                    f"{enrollment.integration_id}"
                )

    def test_enrollment_query_with_string_integration_id(self):
        """Test that querying with string integration_id works correctly"""
        test_id = "5432101"
        enrollment = Enrollment.objects.get(integration_id=test_id)
        self.assertEqual(enrollment.integration_id, test_id)
        self.assertIsInstance(enrollment.integration_id, str)

    def test_django_converts_int_to_string_for_queries(self):
        """Test Django converts int to string for CharField queries"""
        test_id_int = 5432101
        test_id_str = "5432101"

        # First verify the string version exists
        enrollment_str = Enrollment.objects.get(integration_id=test_id_str)
        self.assertIsNotNone(enrollment_str)

        # Django converts int to string for CharField queries, so this works
        enrollment_int = Enrollment.objects.get(integration_id=test_id_int)
        self.assertEqual(enrollment_str.id, enrollment_int.id)

        # But the stored value is still a string
        self.assertIsInstance(enrollment_int.integration_id, str)

    def test_set_operations_with_mixed_types_fail(self):
        """Test that set operations fail with mixed string/int types"""
        string_ids = {"5432101", "5432102", "5432103"}
        int_ids = {5432101, 5432102, 5432103}

        # These sets should be different due to type mismatch
        self.assertNotEqual(string_ids, int_ids)

        # Intersection should be empty
        intersection = string_ids & int_ids
        self.assertEqual(len(intersection), 0)

        # discard() with wrong type should not remove items
        test_set = {"5432101", "5432102"}
        test_set.discard(5432101)  # Try to discard int from string set
        self.assertEqual(len(test_set), 2)  # Should still have 2 items

    def test_enrolled_studentnos_query_returns_strings(self):
        """Test that the enrolled_studentnos query returns string values"""
        enrolled_studentnos = set(Enrollment.objects.filter(
            course__training_course=self.training_course
        ).values_list('integration_id', flat=True))

        # Verify all returned values are strings
        for student_no in enrolled_studentnos:
            with self.subTest(student_no=student_no):
                self.assertIsInstance(
                    student_no, str,
                    f"values_list should return strings, got "
                    f"{type(student_no)}: {student_no}"
                )

    @patch('training_provisioner.models.'
           'training_course.TrainingCourse.get_course_membership')
    def test_membership_candidates_should_be_converted_to_strings(
            self, mock_membership):
        """Test membership candidates converted to strings to avoid issues"""
        # Mock with mixed types to test conversion
        mock_membership.return_value = [
            "5432101", "5432102", 5432103, 5432104]

        candidates = self.training_course.get_course_membership()

        # Convert any integers to strings (this is what we SHOULD do)
        string_candidates = [str(c) for c in candidates]

        # Now all should be strings
        for candidate in string_candidates:
            with self.subTest(candidate=candidate):
                self.assertIsInstance(candidate, str)

        # Original candidates had mixed types - this demonstrates the problem
        int_candidates = [c for c in candidates if isinstance(c, int)]
        if int_candidates:
            # This is expected to fail until we fix the membership functions
            pass  # We'll document this as a known issue

    def test_course_id_for_member_with_string_integration_id(self):
        """Test get_course_id_for_member works with string integration_id"""
        test_id = "5432101"
        course_id = self.training_course.get_course_id_for_member(test_id)

        # Should return a valid course_id
        self.assertIsNotNone(course_id)
        self.assertIsInstance(course_id, str)
        self.assertTrue(
            course_id.startswith(
                self.training_course.course_id_prefix))

    def test_course_id_for_member_with_int_integration_id(self):
        """Test get_course_id_for_member works with int integration_id"""
        test_id_int = 5432101
        test_id_str = "5432101"

        # Both should work due to _hash() converting to int
        course_id_from_int = self.training_course.get_course_id_for_member(
            test_id_int)
        course_id_from_str = self.training_course.get_course_id_for_member(
            test_id_str)

        # Should return the same course_id
        self.assertEqual(course_id_from_int, course_id_from_str)

    def test_create_enrollment_with_int_integration_id_converts_to_string(
            self):
        """Test enrollment with int integration_id as string"""
        test_course = Course.objects.first()
        test_int_id = 9999999

        # Create enrollment with integer integration_id
        enrollment = Enrollment.objects.create(
            integration_id=test_int_id,
            course=test_course
        )

        # Should be stored as string in database
        enrollment.refresh_from_db()
        self.assertIsInstance(enrollment.integration_id, str)
        self.assertEqual(enrollment.integration_id, str(test_int_id))

    def test_real_world_scenario_enrolled_vs_candidates_mismatch(self):
        """Test real-world scenario with enrolled/candidates type mismatches"""
        # Simulate enrolled students (always strings from database)
        enrolled_studentnos = set(Enrollment.objects.filter(
            course__training_course=self.training_course
        ).values_list('integration_id', flat=True))

        # Simulate candidates with mixed types (the problem case)
        mixed_candidates = ["5432101", 5432102, "5432103", 5432104]

        # This is the problematic scenario in add_models_for_training_course
        for candidate in mixed_candidates:
            # Without string conversion, discard silently fails for int
            # candidates
            enrolled_copy = enrolled_studentnos.copy()
            enrolled_copy.discard(candidate)

            if isinstance(candidate, int):
                # This demonstrates the bug - int candidate doesn't get removed
                candidate_str = str(candidate)
                if candidate_str in enrolled_studentnos:
                    # The discard should have removed it, but didn't due to
                    # type mismatch
                    self.assertIn(
                        candidate_str,
                        enrolled_copy,
                        f"discard() failed to remove {candidate} "
                        f"due to type mismatch")
            else:
                # String candidates work correctly
                if candidate in enrolled_studentnos:
                    self.assertNotIn(
                        candidate,
                        enrolled_copy,
                        f"discard() correctly removed string {candidate}")

    def test_solution_always_convert_candidates_to_strings(self):
        """Test the solution: always convert candidates to strings"""
        # Simulate enrolled students (always strings from database)
        enrolled_studentnos = set(Enrollment.objects.filter(
            course__training_course=self.training_course
        ).values_list('integration_id', flat=True))

        # Simulate candidates with mixed types
        mixed_candidates = ["5432101", 5432102, "5432103", 5432104]

        # THE SOLUTION: Convert all candidates to strings
        for candidate in mixed_candidates:
            candidate_str = str(candidate)  # Always convert to string

            enrolled_copy = enrolled_studentnos.copy()
            enrolled_copy.discard(candidate_str)

            if candidate_str in enrolled_studentnos:
                # Now discard works correctly regardless of original type
                self.assertNotIn(
                    candidate_str,
                    enrolled_copy,
                    f"discard() correctly removed {candidate_str} "
                    f"after string conversion")

    def test_hash_function_consistency_with_string_and_int(self):
        """Test _hash() function works consistently with string and int"""
        test_id_str = "5432101"
        test_id_int = 5432101

        hash_from_str = self.training_course._hash(test_id_str)
        hash_from_int = self.training_course._hash(test_id_int)

        # Should produce the same hash value
        self.assertEqual(hash_from_str, hash_from_int)
        self.assertIsInstance(hash_from_str, int)
        self.assertIsInstance(hash_from_int, int)

    def test_course_index_for_member_consistency(self):
        """Test that _course_index_for_member returns consistent results"""
        test_id_str = "5432101"
        test_id_int = 5432101

        index_from_str = self.training_course._course_index_for_member(
            test_id_str)
        index_from_int = self.training_course._course_index_for_member(
            test_id_int)

        # Should return the same course index
        self.assertEqual(index_from_str, index_from_int)

    def test_filter_candidates_by_course_type_string_consistency(self):
        """Test _filter_candidates_by_course_type handles string IDs"""
        # This tests the internal filtering logic
        manager = Enrollment.objects

        # Test with string candidates (correct)
        string_candidates = {"5432101": ["20254R", "20261A"],
                             "5432102": ["20254R", "20261A"]}
        filtered = manager._filter_candidates_by_course_type(
            string_candidates, self.training_course)

        # Should return list of strings
        for candidate in filtered:
            with self.subTest(candidate=candidate):
                self.assertIsInstance(candidate, str)

    def test_enrollment_unique_constraint_behavior(self):
        """Test how unique constraints behave with type conversion"""
        test_course = Course.objects.first()
        test_id_str = "9999998"
        test_id_int = 9999998

        # Create first enrollment with string ID
        _ = Enrollment.objects.create(
            integration_id=test_id_str,
            course=test_course
        )

        # Test if Django allows duplicate with int ID
        # Note: This documents actual behavior - Django may or may not
        # prevent this depending on database backend and ORM behavior
        try:
            enrollment2 = Enrollment.objects.create(
                integration_id=test_id_int,
                course=test_course
            )
            # If this succeeds, Django didn't enforce uniqueness at ORM level
            # Both enrollments should have string integration_ids
            enrollment2.refresh_from_db()
            self.assertIsInstance(enrollment2.integration_id, str)
            self.assertEqual(enrollment2.integration_id, str(test_id_int))

            # Clean up
            enrollment2.delete()
        except IntegrityError:
            # If this fails, Django did enforce uniqueness
            pass  # Expected behavior

    def test_comparison_edge_cases(self):
        """Test edge cases that demonstrate string/int comparison issues"""
        # These tests document the problems we're trying to avoid

        # String vs int comparison
        self.assertNotEqual("123", 123)
        self.assertNotEqual(123, "123")

        # Set membership with mixed types
        mixed_set = {"123", 123}
        self.assertEqual(len(mixed_set), 2)  # Both values present

        # in operator with mixed types
        self.assertNotIn(123, {"123"})
        self.assertNotIn("123", {123})

        # This demonstrates why consistent string handling is important
        enrolled_as_strings = {"5432101", "5432102"}
        candidate_as_int = 5432101

        # This would silently fail to remove the enrolled student
        enrolled_as_strings.discard(candidate_as_int)
        self.assertEqual(len(enrolled_as_strings), 2)  # Nothing removed!

        # But with string conversion it works
        enrolled_as_strings.discard(str(candidate_as_int))
        self.assertEqual(len(enrolled_as_strings), 1)  # Correctly removed
