# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from training_provisioner.models.section import Section
from training_provisioner.models.enrollment import Enrollment
from training_provisioner.builders import Builder
from training_provisioner.csv.format import (
    CourseCSV, SectionCSV, EnrollmentCSV)


class CourseBuilder(Builder):
    """
    Generates import data for Course and Enrollment models.
    """
    def _process(self, course):
        if course.queue_id is not None:
            self.queue_id = course.queue_id

        if course.provisioned_date is None:
            course_data = self._course_data(course)
            if not self.data.add(CourseCSV(**course_data)):
                return

        for section in Section.objects.course_imports(course):
            if section.provisioned_date is None:
                section_data = self._section_data(section)
                if not self.data.add(SectionCSV(**section_data)):
                    return

        for enrollment in Enrollment.objects.course_imports(course):
            if enrollment.provisioned_date is None:
                enrollment_data = self._enrollment_data(enrollment)
                self.data.add(EnrollmentCSV(**enrollment_data))

    def _course_data(self, course):
        return {
            'course_id': course.course_id,
            'short_name': course.training_course.course_name,
            'long_name': course.training_course.course_name,
            'blueprint_course_id':
                course.training_course.blueprint_course_id,
            'term_id': course.training_course.term_id,
            'account_id': course.training_course.account_id,
            'status': course.status
        }

    def _section_data(self, section):
        return {
            'section_id': section.section_id,
            'course_id': section.course.course_id,
            'name': f"Section {section.section_letter}"
        }

    def _enrollment_data(self, enrollment):
        return {
            'course_id': enrollment.course.course_id,
            'section_id': enrollment.section.section_id if (
                enrollment.section) else None,
            'integration_id': enrollment.integration_id.rjust(7, '0'),
            'status': 'active' if enrollment.is_active else 'inactive'
        }
