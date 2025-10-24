# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from training_provisioner.models import Section, Enrollment
from training_provisioner.builders import Builder
from training_provisioner.csv.format import (
    CourseCSV, SectionCSV, TermCSV, EnrollmentCSV)
from training_provisioner.dao.canvas import (
    course_names_from_course_sis_id)


class CourseBuilder(Builder):
    """
    Generates import data for Course and Enrollment models.
    """
    def _process(self, course):
        if course.queue_id is not None:
            self.queue_id = course.queue_id

        self.data.add(CourseCSV(self._course_data(course)))

        for section in Section.objects.filter(course=course):
            self.data.add(SectionCSV(self._section_data(section)))

        for enrollment in Enrollment.objects.filter(course=course):
            self.data.add(EnrollmentsCSV(self._enrollment_data(enrollment))):

        def _course_data(self, course):
            long_name, short_name = course_names_from_course_sis_id(
                course.training_course.blueprint_course_id)
            return {
                'course_id': course.course_id,
                'short_name': short_name,
                'long_name': long_name,
                'blueprint_course_id': \
                    course.training_course.blueprint_course_id,
                'term_id': course.training_course.term_id,
                'account_id': course.training_course.account_id
            }

        def _section_data(self, section):
            return {
                'section_id': section.section_id,
                'course_id': section.course.course_id,
                'name': f"Section {section.section_ordinal}"
            }

        def _enrollment_data(self, enrollment):
            return {
                'integration_id': enrollment.integration_id,
                'course_id': enrollment.course.course_id,
                'section_id': enrollment.section.section_id if (
                    enrollment.section) else ''
            }
