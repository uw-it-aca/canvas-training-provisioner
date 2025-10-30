# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.db import models
from training_provisioner.models.training_course import TrainingCourse
from training_provisioner.models import Course, Import, ImportResource
from training_provisioner.exceptions import MissingCourseException
from django.utils.timezone import localtime
import json
import logging


logger = logging.getLogger(__name__)


class SectionManager(models.Manager):
    def add_sections(self, training_course):
        sections = []
        for course_id in training_course.course_import_ids:
            try:
                course = Course.objects.get(
                    training_course=training_course,
                    course_id=course_id)
            except Course.DoesNotExist:
                raise MissingCourseException(
                    f"Course {course_id} model not found for ")

            for i, section_id in enumerate(course.section_import_ids):
                section, _ = Section.objects.get_or_create(
                    course=course, section_id=section_id,
                    section_ordinal=i + 1)
                sections.append(section)

                if _:
                    logger.info(f"added section {section.section_id}")

        return sections


class Section(models.Model):
    """
    Provisioned Training Course Section
    """
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    section_id = models.CharField(max_length=80, null=True)
    section_ordinal = models.IntegerField()
    created_date = models.DateTimeField(auto_now=True)
    deleted_date = models.DateTimeField(null=True)

    objects = SectionManager()

    @property
    def term_id(self):
        return self.training_course.term_id

    @property
    def status(self):
        return self.training_course.course_status_name

    @property
    def account_id(self):
        return self.training_course.account_id

    def json_data(self):
        return {
            "section_id": self.section_id,
            "section_ordinal": self.section_ordinal,
            "course": self.course.json_data(),
            "created_date": localtime(self.deleted_date).isoformat(),
            "deleted_date": localtime(self.deleted_date).isoformat() if (
                self.deleted_date is not None) else None
        }

    def __str__(self):
        return json.dumps(self.json_data())

    class Meta:
        db_table = 'section'
