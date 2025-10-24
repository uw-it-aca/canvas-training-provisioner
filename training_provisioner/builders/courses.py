# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from training_provisioner.builders import Builder
from training_provisioner.csv.format import (
    CourseCSV, SectionCSV, TermCSV, EnrollmentCSV)


class CourseBuilder(Builder):
    """
    Generates import data for Course and Enrollment models.
    """
    def _process(self, course):
        if course.queue_id is not None:
            self.queue_id = course.queue_id

        self.data.add(CourseCSV(course))
        self.data.add(SectionCSV(course))
        self.data.add(EnrollmentsCSV(course))):
