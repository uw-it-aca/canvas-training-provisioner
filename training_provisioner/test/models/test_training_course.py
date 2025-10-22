# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from training_provisioner.test import TrainingCourseTestCase
from training_provisioner.models import TrainingCourse
from mock import patch


class TrainingCourseModelTest(TrainingCourseTestCase):
    @patch('training_provisioner.models.'
           'training_course.get_title_vi_membership')
    def test_membership(self, mock_membership):
        mock_membership.return_value = self.get_membership()

        course = TrainingCourse.objects.get(pk=1)

        course_id_list = course.course_import_ids
        for i in range(course.course_count):
            self.assertEqual(
                course_id_list[i], f"{course.course_id_prefix}{i+1}")

        members = course.get_membership_for_course()
        self.assertEqual(len(members), len(mock_membership.return_value))

        for i, member in enumerate(members):
            member_course = course.get_course_id_for_member(member)
            self.assertEqual(
                member_course,
                f"{course.course_id_prefix}"
                f"{self.member_course_number(member)}")
