# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from training_provisioner.test import TrainingCourseTestCase
from training_provisioner.models.training_course import TrainingCourse
from training_provisioner.models.course import Course
from training_provisioner.models.section import Section
from training_provisioner.models.enrollment import Enrollment
from mock import patch


class TestAddModelsForTrainingCourse(TrainingCourseTestCase):
    """
    Test add_models_for_training_course() method with various scenarios
    including enrollment creation, updates, and filtering by course type.
    """

    def setUp(self):
        """Set up test data and ensure courses/sections exist"""
        # Get training courses from fixtures.
        # AY2025-2026, 101...
        self.course_101_aya = TrainingCourse.objects.get(pk=1)
        # Skipping AY2025-2026, booster (pk=2) since we wouldn't expect
        #   any enrollments there in these tests
        # AY2026-2027, 101...
        self.course_101_ayb = TrainingCourse.objects.get(pk=3)
        # AY2026-2027, booster...
        self.course_booster_ayb = TrainingCourse.objects.get(pk=4)

        # Create courses and sections for all training courses
        for training_course in [self.course_101_aya,
                                self.course_101_ayb,
                                self.course_booster_ayb]:
            Course.objects.add_models_for_training_course(training_course)
            Section.objects.add_models_for_training_course(training_course)

        # Test course_count courses and section_count sections were created
        for training_course in [self.course_101_aya,
                                self.course_101_ayb,
                                self.course_booster_ayb]:
            # Verify correct number of courses created
            course_count = Course.objects.filter(
                training_course=training_course).count()
            self.assertEqual(
                course_count,
                training_course.course_count,
                f"Expected {training_course.course_count} courses for "
                f"{training_course}, got {course_count}")

            # Verify correct number of sections created per course
            for course in Course.objects.filter(
                    training_course=training_course):
                section_count = Section.objects.filter(course=course).count()
                self.assertEqual(
                    section_count,
                    training_course.section_count,
                    f"Expected {training_course.section_count} sections for "
                    f"course {course.course_id}, got {section_count}")

    @patch('training_provisioner.models.training_course.TrainingCourse.'
           'get_course_membership')
    def test_initial_enrollment_creation(self, mock_membership):
        """
        Test 1: Run with mock course pk=1 and 10 dummy user IDs.
        Verify each gets an enrollment.
        """
        # Set up mock membership for course 1
        user_ids_set1 = ['1001', '1002', '1003', '1004', '1005',
                         '1006', '1007', '1008', '1009', '1010']
        mock_membership.return_value = user_ids_set1

        # Run add_models_for_training_course
        enrollments = Enrollment.objects.add_models_for_training_course(
            self.course_101_aya)

        # Verify all users got enrollments
        self.assertEqual(len(enrollments), 10)

        # Verify each user has an enrollment
        for user_id in user_ids_set1:
            enrollment = Enrollment.objects.get(
                integration_id=user_id,
                course__training_course=self.course_101_aya
            )
            self.assertIsNotNone(enrollment)
            self.assertIsNone(enrollment.deleted_date)

        # Verify total enrollment count
        total_enrollments = Enrollment.objects.filter(
            course__training_course=self.course_101_aya
        ).count()
        self.assertEqual(total_enrollments, 10)

        # Test that users are distributed across courses/sections according
        # to the assignment logic
        user_course_assignments = {}
        user_section_assignments = {}

        for user_id in user_ids_set1:
            enrollment = Enrollment.objects.get(
                integration_id=user_id,
                course__training_course=self.course_101_aya
            )

            # Verify course assignment matches the training course logic
            expected_course_id = self.course_101_aya.\
                get_course_id_for_member(user_id)
            self.assertEqual(
                enrollment.course.course_id, expected_course_id,
                f"User {user_id} assigned to wrong course. Expected "
                f"{expected_course_id}, got {enrollment.course.course_id}")

            # Track course distribution
            course_id = enrollment.course.course_id
            user_course_assignments[course_id] = user_course_assignments.get(
                course_id, 0) + 1

            # Verify section assignment if sections exist
            if self.course_101_aya.section_count > 0:
                expected_section_id = enrollment.course.\
                    get_section_id_for_member(user_id)
                actual_section_id = enrollment.section.section_id if \
                    enrollment.section else None
                self.assertEqual(
                    actual_section_id,
                    expected_section_id,
                    f"User {user_id} assigned to wrong section. Expected "
                    f"{expected_section_id}, got {actual_section_id}")

                # Track section distribution
                if actual_section_id:
                    user_section_assignments[actual_section_id] = \
                        user_section_assignments.get(actual_section_id, 0) + 1

        # Print distribution for visual verification
        print(f"\nCourse distribution for {self.course_101_aya.course_name}:")
        for course_id, count in user_course_assignments.items():
            print(f"  {course_id}: {count} users")

        if user_section_assignments:
            print("Section distribution:")
            for section_id, count in user_section_assignments.items():
                print(f"  {section_id}: {count} users")

    @patch('training_provisioner.models.training_course.TrainingCourse.'
           'get_course_membership')
    def test_rerun_with_same_data_no_duplicates(self, mock_membership):
        """
        Rerun test_initial_enrollment_creation() with exactly the same data
        and verify no duplicates are created and no users are deleted.
        """
        # Use the same user set as test_initial_enrollment_creation
        user_ids_set1 = ['1001', '1002', '1003', '1004', '1005',
                         '1006', '1007', '1008', '1009', '1010']
        mock_membership.return_value = user_ids_set1

        # First run - create initial enrollments
        initial_enrollments = Enrollment.objects.\
            add_models_for_training_course(self.course_101_aya)

        # Capture initial state
        initial_enrollment_data = {}
        for enrollment in initial_enrollments:
            this_section_id = enrollment.section.section_id if \
                enrollment.section else None
            initial_enrollment_data[enrollment.integration_id] = {
                'id': enrollment.id,
                'created_date': enrollment.created_date,
                'deleted_date': enrollment.deleted_date,
                'course_id': enrollment.course.course_id,
                'section_id': this_section_id
            }

        initial_count = len(initial_enrollments)
        self.assertEqual(initial_count, 10)

        # Second run - with exactly the same data
        second_enrollments = Enrollment.objects.add_models_for_training_course(
            self.course_101_aya)

        # Verify no new enrollments were created
        total_enrollments = Enrollment.objects.filter(
            course__training_course=self.course_101_aya
        ).count()
        self.assertEqual(
            total_enrollments,
            10,
            "Second run should not create duplicate enrollments")

        # Verify no users were marked as deleted
        active_enrollments = Enrollment.objects.filter(
            course__training_course=self.course_101_aya,
            deleted_date__isnull=True
        ).count()
        self.assertEqual(active_enrollments, 10,
                         "Second run should not delete any users")

        # Verify each user's enrollment data is unchanged
        for user_id in user_ids_set1:
            enrollment = Enrollment.objects.get(
                integration_id=user_id,
                course__training_course=self.course_101_aya
            )

            initial_data = initial_enrollment_data[user_id]

            # Verify same enrollment record (same ID)
            self.assertEqual(
                enrollment.id,
                initial_data['id'],
                f"User {user_id} should have same enrollment ID")

            # Verify created_date unchanged
            self.assertEqual(
                enrollment.created_date,
                initial_data['created_date'],
                f"User {user_id} created_date should be unchanged")

            # Verify still not deleted
            self.assertIsNone(
                enrollment.deleted_date,
                f"User {user_id} should not be marked as deleted")

            # Verify course/section assignment unchanged
            self.assertEqual(
                enrollment.course.course_id,
                initial_data['course_id'],
                f"User {user_id} course assignment should be unchanged")

            actual_section_id = enrollment.section.section_id if \
                enrollment.section else None
            self.assertEqual(
                actual_section_id,
                initial_data['section_id'],
                f"User {user_id} section assignment should be unchanged")

        print(f"\nRerun test verified: {len(second_enrollments)} existing "
              f"enrollments returned, no duplicates created, no users deleted")

    @patch('training_provisioner.models.training_course.TrainingCourse.'
           'get_course_membership')
    def test_partial_update_enrollment(self, mock_membership):
        """
        Test 2: Run with same course but different user set.
        5 duplicates from previous + 5 new. Verify 5 missing are deleted,
        5 new are created, 5 duplicates unchanged.
        """
        # First, create initial enrollments (same as test 1)
        user_ids_set1 = ['1001', '1002', '1003', '1004', '1005',
                         '1006', '1007', '1008', '1009', '1010']
        mock_membership.return_value = user_ids_set1
        Enrollment.objects.add_models_for_training_course(self.course_101_aya)

        # Now run with new set: 5 duplicates + 5 new
        user_ids_set2 = ['1001', '1002', '1003', '1004', '1005',  # duplicates
                         '1011', '1012', '1013', '1014', '1015']  # new
        mock_membership.return_value = user_ids_set2

        # Store original enrollment dates for duplicates to verify they're
        # unchanged
        original_enrollments = {}
        for user_id in ['1001', '1002', '1003', '1004', '1005']:
            enrollment = Enrollment.objects.get(
                integration_id=user_id,
                course__training_course=self.course_101_aya
            )
            original_enrollments[user_id] = {
                'created_date': enrollment.created_date,
                'deleted_date': enrollment.deleted_date
            }

        # Run add_models_for_training_course again
        _ = Enrollment.objects.add_models_for_training_course(
            self.course_101_aya)

        # Verify 5 new users were created
        new_user_ids = ['1011', '1012', '1013', '1014', '1015']
        for user_id in new_user_ids:
            enrollment = Enrollment.objects.get(
                integration_id=user_id,
                course__training_course=self.course_101_aya
            )
            self.assertIsNotNone(enrollment)
            self.assertIsNone(enrollment.deleted_date)

        # Verify 5 duplicates are unchanged
        duplicate_user_ids = ['1001', '1002', '1003', '1004', '1005']
        for user_id in duplicate_user_ids:
            enrollment = Enrollment.objects.get(
                integration_id=user_id,
                course__training_course=self.course_101_aya
            )
            self.assertEqual(
                enrollment.created_date,
                original_enrollments[user_id]['created_date']
            )
            self.assertIsNone(enrollment.deleted_date)

        # Verify 5 missing users are marked as deleted
        missing_user_ids = ['1006', '1007', '1008', '1009', '1010']
        for user_id in missing_user_ids:
            enrollment = Enrollment.objects.get(
                integration_id=user_id,
                course__training_course=self.course_101_aya
            )
            self.assertIsNotNone(enrollment.deleted_date)

        # Verify total enrollment count (10 original, none deleted from DB)
        total_enrollments = Enrollment.objects.filter(
            course__training_course=self.course_101_aya
        ).count()
        self.assertEqual(total_enrollments, 15)  # 10 original + 5 new

        # Verify active enrollment count (5 existing + 5 new)
        active_enrollments = Enrollment.objects.filter(
            course__training_course=self.course_101_aya,
            deleted_date__isnull=True
        ).count()
        self.assertEqual(active_enrollments, 10)

    @patch('training_provisioner.models.training_course.TrainingCourse.'
           'get_course_membership')
    def test_reenrollment_enrollment(self, mock_membership):
        """
        Test reenrollment of previously deleted users.
        NOTE: This test documents the EXPECTED behavior for reenrollment.
        Currently, the implementation may need to be updated to support
        automatic reenrollment by clearing deleted_date when a previously
        deleted user appears in new membership data.
        """
        # First, establish initial state with enrollments and some deletions
        user_ids_set1 = ['1001', '1002', '1003', '1004', '1005',
                         '1006', '1007', '1008', '1009', '1010']
        mock_membership.return_value = user_ids_set1
        Enrollment.objects.add_models_for_training_course(self.course_101_aya)

        # Remove some users to create deleted enrollments
        user_ids_set2 = ['1001', '1002', '1003', '1004', '1005',
                         '1011', '1012', '1013', '1014', '1015']
        mock_membership.return_value = user_ids_set2
        Enrollment.objects.add_models_for_training_course(self.course_101_aya)

        # Verify that users 1006-1010 are marked as deleted
        previously_deleted_user_ids = ['1006', '1007', '1008', '1009', '1010']
        for user_id in previously_deleted_user_ids:
            enrollment = Enrollment.objects.get(
                integration_id=user_id,
                course__training_course=self.course_101_aya
            )
            self.assertIsNotNone(enrollment.deleted_date)

        # Now attempt to reenroll 2 of the previously deleted users
        reenrolled_users = ['1006', '1007']
        user_ids_set3 = ['1001', '1002', '1003', '1004', '1005',
                         '1011', '1012', '1013', '1014', '1015',
                         '1006', '1007']  # Add back 2 previously deleted users
        mock_membership.return_value = user_ids_set3

        # Run the method - it should NOT re-delete the manually reenrolled
        # users
        Enrollment.objects.add_models_for_training_course(self.course_101_aya)

        # Verify the reenrolled users remain active
        for user_id in reenrolled_users:
            enrollment = Enrollment.objects.get(
                integration_id=user_id,
                course__training_course=self.course_101_aya
            )
            self.assertIsNone(enrollment.deleted_date,
                              f"User {user_id} should remain reenrolled")

        # Verify that the other previously deleted users remain deleted
        still_deleted_users = ['1008', '1009', '1010']
        for user_id in still_deleted_users:
            enrollment = Enrollment.objects.get(
                integration_id=user_id,
                course__training_course=self.course_101_aya
            )
            self.assertIsNotNone(enrollment.deleted_date,
                                 f"User {user_id} should remain deleted")

        # Count active enrollments (may vary based on implementation)
        active_enrollments = Enrollment.objects.filter(
            course__training_course=self.course_101_aya,
            deleted_date__isnull=True
        ).count()

        # 5 original + 5 new + 2 reenrolled = 12
        expected_active = 12
        self.assertEqual(active_enrollments, expected_active,
                         f"Expected {expected_active} active enrollments, "
                         f"got {active_enrollments}")

        # Verify total enrollment count remains the same
        total_enrollments = Enrollment.objects.filter(
            course__training_course=self.course_101_aya
        ).count()
        self.assertEqual(total_enrollments, 15)  # 10 original + 5 new

    @patch('training_provisioner.models.training_course.TrainingCourse.'
           'get_course_membership')
    def test_different_course_enrollment(self, mock_membership):
        """
        Test 3:
        Run with course pk=3 (different academic year) and same user set
        from test 2 plus 5 new users. Verify users who were deleted are created
        and users who were active are not created, and new users are created.
        """
        # First, run tests 1 and 2 to establish state for course 1
        user_ids_set1 = ['1001', '1002', '1003', '1004', '1005',
                         '1006', '1007', '1008', '1009', '1010']
        mock_membership.return_value = user_ids_set1
        Enrollment.objects.add_models_for_training_course(self.course_101_aya)

        user_ids_set2 = ['1001', '1002', '1003', '1004', '1005',
                         '1011', '1012', '1013', '1014', '1015']
        mock_membership.return_value = user_ids_set2
        Enrollment.objects.add_models_for_training_course(self.course_101_aya)

        # Now run with course 3 (AY2026-2027, also 101 type)
        # Using set2 users + 5 entirely new users
        # - 1001-1005: were active in course 1
        # - 1011-1015:  were active in course 1
        # - 1006-1010:  were deleted in course 1
        # - 1016-1020:  entirely new
        user_ids_set3 = ['1001', '1002', '1003', '1004', '1005',
                         '1011', '1012', '1013', '1014', '1015',
                         '1006', '1007', '1008', '1009', '1010',
                         '1016', '1017', '1018', '1019', '1020']
        mock_membership.return_value = user_ids_set3

        # Run add_models_for_training_course for course 3
        _ = Enrollment.objects.add_models_for_training_course(
            self.course_101_ayb)

        # Since course 3 is also type '101' and different academic year,
        # users with previous 101 enrollments should be excluded
        # So only users who were deleted or entirely new should be enrolled

        # Users who were deleted in course 1 should be created in course 3
        previously_deleted = ['1006', '1007', '1008', '1009', '1010']
        for user_id in previously_deleted:
            enrollment = Enrollment.objects.get(
                integration_id=user_id,
                course__training_course=self.course_101_ayb
            )
            self.assertIsNotNone(enrollment)
            self.assertIsNone(enrollment.deleted_date)

        # Entirely new users should be created in course 3
        entirely_new = ['1016', '1017', '1018', '1019', '1020']
        for user_id in entirely_new:
            enrollment = Enrollment.objects.get(
                integration_id=user_id,
                course__training_course=self.course_101_ayb
            )
            self.assertIsNotNone(enrollment)
            self.assertIsNone(enrollment.deleted_date)

        # Users who were active in course 1 should NOT be created in course 3
        # (due to _has_previous_101_enrollment filtering)
        previously_active = ['1001', '1002', '1003', '1004', '1005',
                             '1011', '1012', '1013', '1014', '1015']
        for user_id in previously_active:
            with self.assertRaises(Enrollment.DoesNotExist):
                Enrollment.objects.get(
                    integration_id=user_id,
                    course__training_course=self.course_101_ayb
                )

        # Verify total enrollment count for course 3 (5 deleted + 5 new = 10)
        total_enrollments = Enrollment.objects.filter(
            course__training_course=self.course_101_ayb
        ).count()
        self.assertEqual(total_enrollments, 10)

    @patch('training_provisioner.models.training_course.TrainingCourse.'
           'get_course_membership')
    def test_booster_course_enrollment(self, mock_membership):
        """
        Test 4: Run with course pk=4 (booster type) and same user set as test 2
        Only users who were created in the previous quarter and not deleted
        should appear in this course.
        """
        # First, establish state from tests 1 and 2
        user_ids_set1 = ['1001', '1002', '1003', '1004', '1005',
                         '1006', '1007', '1008', '1009', '1010']
        mock_membership.return_value = user_ids_set1
        Enrollment.objects.add_models_for_training_course(self.course_101_aya)

        user_ids_set2 = ['1001', '1002', '1003', '1004', '1005',
                         '1011', '1012', '1013', '1014', '1015']
        mock_membership.return_value = user_ids_set2
        Enrollment.objects.add_models_for_training_course(self.course_101_aya)

        # Now run with booster course (pk=4, type 'booster', AY2026-2027)
        # Using same set as test 2
        mock_membership.return_value = user_ids_set2

        # Run add_models_for_training_course for booster course
        _ = Enrollment.objects.add_models_for_training_course(
            self.course_booster_ayb)

        # For booster courses, only users who have previous 101 enrollment
        # from different academic year should be included
        # Since course 1 (AY2025-2026) is different from course 4 (AY2026-2027)
        # users with active enrollments in course 1 should be eligible

        # Users who were active in course 1 and are in the candidate list
        # should be enrolled in booster course
        active_in_previous = ['1001', '1002', '1003', '1004', '1005',
                              '1011', '1012', '1013', '1014', '1015']
        for user_id in active_in_previous:
            enrollment = Enrollment.objects.get(
                integration_id=user_id,
                course__training_course=self.course_booster_ayb
            )
            self.assertIsNotNone(enrollment)
            self.assertIsNone(enrollment.deleted_date)

        # Verify total enrollment count for booster course
        total_enrollments = Enrollment.objects.filter(
            course__training_course=self.course_booster_ayb
        ).count()
        self.assertEqual(total_enrollments, 10)

    @patch('training_provisioner.models.training_course.TrainingCourse.'
           'get_course_membership')
    def test_enrollment_course_mismatch_handling(self, mock_membership):
        """
        Test that enrollments maintain course/section consistency
        """
        user_ids = ['1001', '1002']
        mock_membership.return_value = user_ids

        # Create initial enrollments
        Enrollment.objects.add_models_for_training_course(self.course_101_aya)

        # Verify enrollments were created
        self.assertEqual(
            Enrollment.objects.filter(
                course__training_course=self.course_101_aya
            ).count(),
            2
        )

        # Run again with same membership - should not create duplicates
        enrollments = Enrollment.objects.add_models_for_training_course(
            self.course_101_aya)

        # Should return existing enrollments, not create new ones
        self.assertEqual(len(enrollments), 2)
        self.assertEqual(
            Enrollment.objects.filter(
                course__training_course=self.course_101_aya
            ).count(),
            2
        )

    def test_filter_candidates_by_course_type_101(self):
        """
        Test that 101 courses properly filter out users with previous 101
        enrollments
        """
        # Create some enrollments in course 1 (AY2025-2026, 101)
        user_ids = ['1001', '1002', '1003']

        for user_id in user_ids:
            course = Course.objects.filter(
                training_course=self.course_101_aya).first()
            Enrollment.objects.create(integration_id=user_id, course=course)

        # Test filtering for course 3 (AY2026-2027, 101)
        # 1001,1002 have previous, 1004,1005 don't
        candidates = ['1001', '1002', '1004', '1005']

        filtered = Enrollment.objects._filter_candidates_by_course_type(
            candidates, self.course_101_ayb
        )

        # Only users without previous 101 enrollments should be included
        self.assertEqual(set(filtered), {'1004', '1005'})

    def test_filter_candidates_by_course_type_booster(self):
        """
        Test that booster courses properly filter to only include users with
        previous 101 enrollments
        """
        # Create some enrollments in course 1 (AY2025-2026, 101)
        user_ids = ['1001', '1002', '1003']

        for user_id in user_ids:
            course = Course.objects.filter(
                training_course=self.course_101_aya).first()
            Enrollment.objects.create(integration_id=user_id, course=course)

        # Test filtering for booster course (AY2026-2027, booster)
        # 1001,1002 have previous, 1004,1005 don't
        candidates = ['1001', '1002', '1004', '1005']

        filtered = Enrollment.objects._filter_candidates_by_course_type(
            candidates, self.course_booster_ayb
        )

        # Only users WITH previous 101 enrollments should be included
        self.assertEqual(set(filtered), {'1001', '1002'})

    def test_has_previous_101_enrollment(self):
        """
        Test the _has_previous_101_enrollment helper method
        """
        # Create enrollment in course 1 (AY2025-2026, 101)
        user_id = '1001'
        course = Course.objects.filter(
            training_course=self.course_101_aya).first()
        Enrollment.objects.create(integration_id=user_id, course=course)

        # Test against course 3 (AY2026-2027, 101) - different academic year
        has_previous = Enrollment.objects._has_previous_101_enrollment(
            user_id, self.course_101_ayb
        )
        self.assertTrue(has_previous)

        # Test with user who has no previous enrollment
        has_previous = Enrollment.objects._has_previous_101_enrollment(
            '1002', self.course_101_ayb
        )
        self.assertFalse(has_previous)

        # Test against same course (should return False - same academic year)
        has_previous = Enrollment.objects._has_previous_101_enrollment(
            user_id, self.course_101_aya
        )
        self.assertFalse(has_previous)
