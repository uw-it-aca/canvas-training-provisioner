# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from training_provisioner.test import TrainingCourseTestCase
from training_provisioner.models import TrainingCourse, Course, Section
    

class SectionModelTest(TrainingCourseTestCase):
    def test_course_model(self):
        for training_course in TrainingCourse.objects.active_courses():
            Course.objects.add_courses(training_course)
            Section.objects.add_sections(training_course)

            sections = Section.objects.all()

            self.assertEqual(
                sections.count(), 
                (training_course.course_count *
                 training_course.section_count))

            if training_course.section_count > 0:
                self.assertEqual(
                    len(set(sections.values_list('course__id', flat=True))),
                    training_course.course_count)

            Course.objects.all().delete()
            Section.objects.all().delete()

