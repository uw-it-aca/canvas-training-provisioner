# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from training_provisioner.test import TrainingCourseTestCase
from training_provisioner.models.training_course import TrainingCourse
from training_provisioner.views.api.enrollments import Enrollments
from django.test.client import RequestFactory
from django.urls import reverse_lazy
import json


class EnrollmentsAPITest(TrainingCourseTestCase):
    def test_get_enrollments(self):
        for training_course in TrainingCourse.objects.active_courses():
            training_course.load_courses_and_enrollments()

        enrollments_api = Enrollments()
        url = reverse_lazy('student_enrollments',
                           kwargs={'integration_id': '5432101'})
        request = RequestFactory().get(url)
        response = enrollments_api.get(request, integration_id='5432101')
        enrollments = json.loads(response.content)

        # Student 5432101 should be enrolled in 2 courses:
        # 1. AY2025-2026-101 (initial 101 course)
        # 2. AY2026-2027-B (booster course for next academic year)
        # They are excluded from AY2025-2026-B due to being in 101 course for
        #    same academic year
        # They are excluded from AY2026-2027-101 due to having previous 101
        #    enrollment
        self.assertEqual(len(enrollments), 2)
