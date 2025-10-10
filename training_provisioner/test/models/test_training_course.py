# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.test import TestCase
from training_provisioner.models import TrainingCourse
from mock import patch


class TrainingCourseModelTest(TestCase):
    fixtures = ['test_data/training_course.json']

    @patch('training_provisioner.models.'
           'training_course.get_title_vi_membership')
    def test_membership(self, mock_membership):
        mock_membership.return_value = ['12345678', '12345679']

        course = TrainingCourse.objects.get(pk=1)

        course_id_list = course.get_all_course_sis_import_ids()
        self.assertEqual(course_id_list[0], 'BLUEPRINT_123-2025-2026-0')
        self.assertEqual(course_id_list[1], 'BLUEPRINT_123-2025-2026-1')

        members = course.get_membership_for_course()
        self.assertEqual(len(members), 2)

        for i, member in enumerate(members):
            member_course = course.get_course_id_for_member(member)
            self.assertEqual(member_course, course_id_list[i])
