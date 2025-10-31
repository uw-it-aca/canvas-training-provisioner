# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from training_provisioner.test import TrainingCourseTestCase
from training_provisioner.models import ImportResource
from training_provisioner.models.training_course import TrainingCourse
from training_provisioner.models.course import Course


class CourseModelTest(TrainingCourseTestCase):
    def test_course_model(self):
        for training_course in TrainingCourse.objects.active_courses():
            Course.objects.add_courses(training_course)

            courses = Course.objects.all()
            self.assertEqual(courses.count(), training_course.course_count)

            self.assertEqual(
                len(set(courses.values_list(
                    'training_course__blueprint_course_id', flat=True))), 1)

            self.assertEqual(courses.filter(
                priority=ImportResource.PRIORITY_DEFAULT).count(),
                             training_course.course_count)

            Course.objects.all().delete()
