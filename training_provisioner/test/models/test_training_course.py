# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from training_provisioner.test import TrainingCourseTestCase
from training_provisioner.models.training_course import TrainingCourse
from training_provisioner.models.course import Course
from training_provisioner.models.section import Section
from training_provisioner.models.enrollment import Enrollment
from mock import patch


class TrainingCourseModelTest(TrainingCourseTestCase):
    def test_load_active_courses(self):
        self.call_load_training_courses()

        courses = TrainingCourse.objects.active_courses()
        self.assertEqual(courses.count(), 4)

    @patch('training_provisioner.models.'
           'training_course.TrainingCourse.get_course_membership')
    def test_membership(self, mock_membership):
        mock_membership.return_value = self.get_membership()
        course = TrainingCourse.objects.get(pk=1)
        course_id_list = course.course_import_ids

        for i in range(course.course_count):
            self.assertEqual(
                course_id_list[i], f"{course.course_id_prefix}{(i+1):03d}")

        members = course.get_course_membership()
        self.assertEqual(len(members), len(mock_membership.return_value))

        for i, member in enumerate(members):
            member_course = course.get_course_id_for_member(member)
            self.assertEqual(
                member_course,
                (f"{course.course_id_prefix}"
                 f"{self.member_course_number(member):03d}"))

    def test_training_course_save(self):
        training_course = TrainingCourse.objects.get(pk=1)
        training_course.load_courses_and_enrollments()

        # simulate post-provision state
        updated = Course.objects.filter(
            training_course=training_course).update(
                priority=Course.PRIORITY_NONE)

        training_course.course_name = "New Name"
        training_course.save()

        self.assertEqual(Course.objects.filter(
            training_course=training_course,
            priority__gt=Course.PRIORITY_NONE).count(), updated)

    @patch('training_provisioner.models.'
           'training_course.TrainingCourse.get_course_membership')
    def test_training_course_cascade_deletion(self, mock_membership):
        """
        Test that deleting a TrainingCourse cascades to all related objects.
        """
        # Setup test data
        mock_membership.return_value = self.get_membership()
        training_course = TrainingCourse.objects.get(pk=1)

        # Load all related models (courses, sections, enrollments)
        training_course.load_courses_and_enrollments()

        # Verify related objects exist
        courses = Course.objects.filter(training_course=training_course)
        sections = Section.objects.filter(
            course__training_course=training_course)
        enrollments = Enrollment.objects.filter(
            course__training_course=training_course)

        initial_course_count = courses.count()
        # No sections currently
        # initial_section_count = sections.count()
        initial_enrollment_count = enrollments.count()

        # Ensure we have related objects to delete
        self.assertGreater(
            initial_course_count,
            0,
            "Should have courses to test deletion")
        self.assertGreater(
            initial_enrollment_count,
            0,
            "Should have enrollments to test deletion")

        # Store the training course ID for verification
        training_course_id = training_course.id

        # Delete the training course - this should CASCADE to all related objs
        training_course.delete()

        # Verify training course is deleted
        self.assertFalse(
            TrainingCourse.objects.filter(id=training_course_id).exists(),
            "TrainingCourse should be deleted"
        )

        # Verify all related objects are CASCADE deleted
        self.assertEqual(
            Course.objects.filter(
                id__in=courses.values_list('id', flat=True)).count(),
            0,
            "All related courses should be CASCADE deleted"
        )

        self.assertEqual(
            Section.objects.filter(
                id__in=sections.values_list('id', flat=True)).count(),
            0,
            "All related sections should be CASCADE deleted"
        )

        self.assertEqual(
            Enrollment.objects.filter(
                id__in=enrollments.values_list('id', flat=True)).count(),
            0,
            "All related enrollments should be CASCADE deleted"
        )

        # Verify other training courses and their data are not affected
        remaining_training_courses = TrainingCourse.objects.all().count()
        self.assertGreater(
            remaining_training_courses,
            0,
            "Other training courses should remain")

    def test_training_course_deletion_with_no_related_objects(self):
        """
        Test that deleting a TrainingCourse with no related objects works.
        """
        # Get a training course that hasn't been loaded with related objects
        training_course = TrainingCourse.objects.get(pk=2)

        # Verify no related objects exist
        self.assertEqual(
            Course.objects.filter(training_course=training_course).count(),
            0,
            "Should have no related courses"
        )

        # Delete should work without error
        training_course.delete()

        # Verify it's deleted
        self.assertFalse(
            TrainingCourse.objects.filter(pk=2).exists(),
            "TrainingCourse should be deleted"
        )
