# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

"""
Test suite for TrainingCourse deletion behavior.

This test suite verifies that TrainingCourse deletion works correctly with
CASCADE deletion of related objects (Course, Section, Enrollment) and
distinguishes between hard deletion (.delete()) and soft deletion (setting
deleted_date).

Tests cover:
- CASCADE deletion of all related models when TrainingCourse is deleted
- Soft deletion via deleted_date field leaves related objects intact
    - Note: Soft deletion is not currently implemented, but this test is in
    place for future functionality. Delete in Django admin currently performs
    hard deletion.
- Deletion isolation between different TrainingCourse instances
- Deletion of TrainingCourse without related data
- Course priority handling during deletion
"""

from django.utils import timezone
from training_provisioner.test import TrainingCourseTestCase
from training_provisioner.models.training_course import TrainingCourse
from training_provisioner.models.course import Course
from training_provisioner.models.enrollment import Enrollment
from training_provisioner.models.section import Section
from mock import patch


class TrainingCourseDeletionTest(TrainingCourseTestCase):

    @patch('training_provisioner.models.'
           'training_course.TrainingCourse.get_course_membership')
    def test_delete_training_course_with_courses_and_enrollments(
            self, mock_membership):
        """Test deleting TrainingCourse with related courses/enrollments"""
        # Setup: Load training courses and create related data
        mock_membership.return_value = self.get_membership()
        self.call_load_training_courses()

        # Get a training course with data
        training_course = TrainingCourse.objects.get(pk=1)
        initial_course_count = Course.objects.filter(
            training_course=training_course).count()
        initial_enrollment_count = Enrollment.objects.filter(
            course__training_course=training_course).count()

        # Verify we have related data to test deletion
        self.assertGreater(initial_course_count, 0,
                           "Should have courses to test deletion")
        self.assertGreater(initial_enrollment_count, 0,
                           "Should have enrollments to test deletion")

        # Store IDs for verification after deletion
        course_ids = list(Course.objects.filter(
            training_course=training_course).values_list('id', flat=True))
        enrollment_ids = list(Enrollment.objects.filter(
            course__training_course=training_course).values_list(
                'id', flat=True))
        section_ids = list(Section.objects.filter(
            course__training_course=training_course).values_list(
                'id', flat=True))

        # Verify initial state
        self.assertEqual(Course.objects.filter(
            id__in=course_ids).count(), initial_course_count)
        self.assertEqual(Enrollment.objects.filter(
            id__in=enrollment_ids).count(), initial_enrollment_count)

        # Perform the deletion
        training_course.delete()

        # Verify TrainingCourse is deleted
        self.assertFalse(TrainingCourse.objects.filter(pk=1).exists())

        # Verify CASCADE deletion of related objects
        self.assertEqual(Course.objects.filter(id__in=course_ids).count(), 0,
                         "All related courses should be deleted via CASCADE")
        self.assertEqual(
            Enrollment.objects.filter(id__in=enrollment_ids).count(), 0,
            "All related enrollments should be deleted via CASCADE")
        self.assertEqual(
            Section.objects.filter(id__in=section_ids).count(), 0,
            "All related sections should be deleted via CASCADE")

    @patch('training_provisioner.models.'
           'training_course.TrainingCourse.get_course_membership')
    def test_soft_delete_training_course(self, mock_membership):
        """Test soft deletion by setting deleted_date instead of actual"""
        # Setup: Load training courses and create related data
        mock_membership.return_value = self.get_membership()
        self.call_load_training_courses()

        # Get a training course with data
        training_course = TrainingCourse.objects.get(pk=1)
        initial_course_count = Course.objects.filter(
            training_course=training_course).count()
        initial_enrollment_count = Enrollment.objects.filter(
            course__training_course=training_course).count()

        # Verify we have related data
        self.assertGreater(initial_course_count, 0)
        self.assertGreater(initial_enrollment_count, 0)
        self.assertIsNone(training_course.deleted_date)

        # Perform soft deletion
        training_course.deleted_date = timezone.now()
        training_course.save()

        # Verify TrainingCourse still exists but is marked as deleted
        updated_training_course = TrainingCourse.objects.get(pk=1)
        self.assertIsNotNone(updated_training_course.deleted_date)

        # Verify related objects are NOT deleted with soft deletion
        self.assertEqual(
            Course.objects.filter(training_course=training_course).count(),
            initial_course_count,
            "Related courses should NOT be deleted with soft deletion")
        self.assertEqual(
            Enrollment.objects.filter(
                course__training_course=training_course).count(),
            initial_enrollment_count,
            "Related enrollments should NOT be deleted with soft deletion")

        # Verify soft-deleted courses are filtered out by active_courses()
        active_courses = TrainingCourse.objects.active_courses()
        self.assertNotIn(
            updated_training_course, active_courses,
            "Soft-deleted training course should not appear in "
            "active_courses()")

    @patch('training_provisioner.models.'
           'training_course.TrainingCourse.get_course_membership')
    def test_delete_multiple_training_courses_with_shared_data(
            self, mock_membership):
        """Test deleting multiple TrainingCourses to verify isolation"""
        # Setup: Load training courses and create related data
        mock_membership.return_value = self.get_membership()
        self.call_load_training_courses()

        # Get two different training courses - use courses that have data
        training_course_1 = TrainingCourse.objects.get(pk=1)  # 101
        training_course_4 = TrainingCourse.objects.get(pk=4)  # Booster

        # Store PKs for queries after deletion
        training_course_1_pk = training_course_1.pk
        training_course_4_pk = training_course_4.pk

        course_1_count = Course.objects.filter(
            training_course=training_course_1).count()
        course_4_count = Course.objects.filter(
            training_course=training_course_4).count()

        enrollment_1_count = Enrollment.objects.filter(
            course__training_course=training_course_1).count()
        enrollment_4_count = Enrollment.objects.filter(
            course__training_course=training_course_4).count()

        # Verify both have data
        self.assertGreater(course_1_count, 0)
        self.assertGreater(course_4_count, 0)
        self.assertGreater(enrollment_1_count, 0)
        self.assertGreater(enrollment_4_count, 0)

        # Delete only the first training course
        training_course_1.delete()

        # Verify only first training course and its data are deleted
        self.assertFalse(TrainingCourse.objects.filter(
            pk=training_course_1_pk).exists())
        self.assertTrue(TrainingCourse.objects.filter(
            pk=training_course_4_pk).exists())

        # Verify first training course's data is deleted
        # (using pk since instance is deleted)
        self.assertEqual(Course.objects.filter(
            training_course__pk=training_course_1_pk).count(), 0)
        self.assertEqual(Enrollment.objects.filter(
            course__training_course__pk=training_course_1_pk).count(), 0)

        # Verify second training course's data is intact
        self.assertEqual(Course.objects.filter(
            training_course=training_course_4).count(), course_4_count)
        self.assertEqual(Enrollment.objects.filter(
            course__training_course=training_course_4).count(),
            enrollment_4_count)

    def test_delete_training_course_without_related_data(self):
        """Test deleting TrainingCourse with no related courses/enrollments"""
        # Create a training course without loading courses/enrollments
        training_course = TrainingCourse(
            course_name="Test Course",
            blueprint_course_id="TEST_BLUEPRINT",
            term_id="TEST_TERM",
            account_id="TEST_ACCOUNT",
            membership_type=TrainingCourse.TEST_MEMBERS,
            course_count=1,
            section_count=0,
            is_provisioned=True
        )
        training_course.save()

        course_count_before = Course.objects.filter(
            training_course=training_course).count()
        enrollment_count_before = Enrollment.objects.filter(
            course__training_course=training_course).count()

        # Verify no related data exists
        self.assertEqual(course_count_before, 0,
                         "Should have no courses initially")
        self.assertEqual(enrollment_count_before, 0,
                         "Should have no enrollments initially")

        # Delete the training course
        training_course_pk = training_course.pk
        training_course.delete()

        # Verify deletion completed successfully
        self.assertFalse(TrainingCourse.objects.filter(
            pk=training_course_pk).exists(),
            "TrainingCourse should be deleted")

    @patch('training_provisioner.models.'
           'training_course.TrainingCourse.get_course_membership')
    def test_delete_affects_course_priorities(self, mock_membership):
        """Test that deleting training course affects course priorities"""
        # Setup: Load training courses and create related data
        mock_membership.return_value = self.get_membership()
        self.call_load_training_courses()

        # Get a training course and modify its courses' priorities
        training_course = TrainingCourse.objects.get(pk=1)
        courses = Course.objects.filter(training_course=training_course)

        # Set some courses to different priorities
        courses.update(priority=Course.PRIORITY_HIGH)

        high_priority_count_before = Course.objects.filter(
            priority=Course.PRIORITY_HIGH).count()
        self.assertGreater(high_priority_count_before, 0,
                           "Should have high priority courses")

        # Delete the training course
        training_course.delete()

        # Verify high priority courses related to deleted course are gone
        high_priority_count_after = Course.objects.filter(
            priority=Course.PRIORITY_HIGH).count()
        self.assertEqual(
            high_priority_count_after, 0,
            "High priority courses should be deleted with training course")
