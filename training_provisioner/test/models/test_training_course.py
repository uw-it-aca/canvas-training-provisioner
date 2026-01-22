# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from training_provisioner.test import TrainingCourseTestCase
from training_provisioner.models.training_course import TrainingCourse
from training_provisioner.models.course import Course
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
