# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.db import models
from training_provisioner.models import ImportResource
from training_provisioner.models.training_course import TrainingCourse
from training_provisioner.models.course import Course
from training_provisioner.exceptions import MissingCourseException
from django.utils.timezone import localtime
import json
import logging


logger = logging.getLogger(__name__)


class SectionManager(models.Manager):
    def add_models_for_training_course(self, training_course):
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
                    course=course, section_id=section_id, defaults={
                        'priority': Section.PRIORITY_DEFAULT,
                        'section_ordinal': i + 1})
                sections.append(section)

                if _:
                    logger.info(f"added section {section.section_id}")

        return sections

    def course_imports(self, course):
        pks = super(SectionManager, self).get_queryset().filter(
            course=course.id,
            priority__gt=ImportResource.PRIORITY_NONE,
            queue_id__isnull=True
        ).values_list('pk', flat=True)

        super(SectionManager, self).get_queryset().filter(
            pk__in=list(pks)).update(queue_id=course.queue_id)

        return super(SectionManager, self).get_queryset().filter(
            pk__in=list(pks))

    def queued(self, queue_id):
        return super(SectionManager, self).get_queryset().filter(
            queue_id=queue_id)

    def dequeue(self, sis_import):
        if sis_import.is_imported():
            # Decrement the priority
            super(SectionManager, self).get_queryset().filter(
                queue_id=sis_import.pk, priority__gt=Section.PRIORITY_NONE
            ).update(
                queue_id=None, priority=F('priority') - 1)
        else:
            self.queued(sis_import.pk).update(queue_id=None)


class Section(ImportResource):
    """
    Provisioned Training Course Section
    """
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    section_id = models.CharField(max_length=80, null=True)
    section_ordinal = models.IntegerField()
    created_date = models.DateTimeField(auto_now=True)
    provisioned_date = models.DateTimeField(null=True)
    deleted_date = models.DateTimeField(null=True)
    priority = models.SmallIntegerField(
        default=ImportResource.PRIORITY_DEFAULT,
        choices=ImportResource.PRIORITY_CHOICES)
    queue_id = models.CharField(max_length=30, null=True)

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
            "provisioned_date": localtime(
                self.provisioned_date).isoformat() if (
                    self.provisioned_date is not None) else None,
            "deleted_date": localtime(self.deleted_date).isoformat() if (
                self.deleted_date is not None) else None
        }

    def __str__(self):
        return json.dumps(self.json_data())

    class Meta:
        db_table = 'section'
