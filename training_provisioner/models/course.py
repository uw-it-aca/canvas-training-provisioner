# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.db import models
from django.db.models import F
from training_provisioner.models.training_course import TrainingCourse
from training_provisioner.models import Import, ImportResource
from training_provisioner.exceptions import EmptyQueueException
from django.utils.timezone import localtime
import json
import logging


logger = logging.getLogger(__name__)


class CourseManager(models.Manager):
    def add_courses(self, training_course):
        courses = []
        for i, course_id in enumerate(training_course.course_import_ids):
            course, _ = Course.objects.get_or_create(
                course_id=course_id, defaults={
                    'training_course': training_course,
                    'course_ordinal': i + 1,
                    'priority': Course.PRIORITY_DEFAULT
                })

            courses.append(course)

            if _:
                logger.info(f"added course {course.course_id}")

        return courses

    def get_courses_by_priority(self, priority):
        return self.filter(priority=priority, deleted_date__isnull=True)

    def queue_by_priority(self, priority):
        kwargs = {
            'priority': priority,
            'queue_id__isnull': True,
            'provisioned_error__isnull': True
        }

        pks = super().get_queryset().filter(**kwargs).order_by(
            F('provisioned_date').asc(nulls_first=True)
        ).values_list('pk', flat=True)

        if not len(pks):
            raise EmptyQueueException()

        imp = Import(priority=priority, csv_type='course')
        imp.save()

        super().get_queryset().filter(pk__in=list(pks)).update(
            queue_id=imp.pk)

        return imp

    def queued(self, queue_id):
        return super(CourseManager, self).get_queryset().filter(
            queue_id=queue_id)

    def dequeue(self, sis_import):
        if sis_import.is_imported():
            # Decrement the priority
            super(CourseManager, self).get_queryset().filter(
                queue_id=sis_import.pk, priority__gt=Course.PRIORITY_NONE
            ).update(
                queue_id=None, priority=F('priority') - 1)
        else:
            self.queued(sis_import.pk).update(queue_id=None)


class Course(ImportResource):
    """
    Provisioned Training Course
    """
    training_course = models.ForeignKey(
        TrainingCourse, on_delete=models.CASCADE)
    course_id = models.CharField(max_length=80, db_index=True, unique=True)
    course_ordinal = models.IntegerField()
    created_date = models.DateTimeField(auto_now=True)
    provisioned_date = models.DateTimeField(null=True)
    provisioned_error = models.BooleanField(null=True)
    provisioned_status = models.CharField(max_length=512, null=True)
    deleted_date = models.DateTimeField(null=True)
    priority = models.SmallIntegerField(
        default=ImportResource.PRIORITY_NONE,
        choices=ImportResource.PRIORITY_CHOICES)
    queue_id = models.CharField(max_length=30, null=True)

    objects = CourseManager()

    @property
    def term_id(self):
        return self.training_course.term_id

    @property
    def status(self):
        return self.training_course.course_status_name

    @property
    def account_id(self):
        return self.training_course.account_id

    @property
    def section_import_ids(self):
        return [f"{self._section_id(i)}" for i in range(
            self.training_course.section_count)]

    def get_section_id_for_member(self, integration_id):
        section_index = self._section_index_for_member(integration_id)
        return self._section_id(section_index) if (
            section_index is not None) else None

    def _section_index_for_member(self, integration_id):
        """
        Which of the self.section_count courses the
        member with integration_id is enrolled
        """
        return (self._hash(integration_id) %
                self.training_course.section_count) if (
                    self.training_course.section_count) else None

    def _section_id(self, index):
        ordinal = index + 1
        return (f"{self.course_id}-{ordinal}-")

    def _hash(self, integration_id):
        """
        Simple hash function for distributing members across sections
        NOTE: must be distinct from _hash function in TrainingCourse
        """
        hash_value = 0
        for char in str(integration_id):
            hash_value += ord(char)

        return hash_value

    def json_data(self):
        return {
            "training_course": self.training_course.json_data(),
            "course_id": self.course_id,
            "term_id": self.term_id,
            "status": self.status,
            "account_id": self.account_id,
            "created_date": localtime(self.deleted_date).isoformat(),
            "provisioned_date": localtime(self.provisioned_date).isoformat() if (
                self.provisioned_date is not None) else None,
            "deleted_date": localtime(self.deleted_date).isoformat() if (
                self.deleted_date is not None) else None,
            "priority": Course.PRIORITY_CHOICES[self.priority][1],
            "queue_id": self.queue_id,
        }

    def __str__(self):
        return json.dumps(self.json_data())

    class Meta:
        db_table = 'course'
