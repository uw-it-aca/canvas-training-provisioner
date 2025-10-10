# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.db import models
from training_provisioner.models.training_course import TrainingCourse
from training_provisioner.models import Import, ImportResource
from django.utils.timezone import localtime
import json


class CourseManager(models.Manager):
    def add_courses(self, training_course):
        for course_id in training_course.course_import_ids:
            course, _ = Course.objects.get_or_create(
                course_id=course_id, defaults={
                    'training_course': training_course,
                    'priority': ImportResource.PRIORITY_DEFAULT
                })

    def get_courses_by_priority(self, priority):
        return self.filter(priority=priority, deleted_date__isnull=True)

    def queue_by_priority(self, priority, term=None):
        filter_limit = settings.SIS_IMPORT_LIMIT['course']['default']
        kwargs = {
            'priority': priority,
            'queue_id__isnull': True,
            'provisioned_error__isnull': True
        }

        pks = super().get_queryset().filter(**kwargs).order_by(
            F('provisioned_date').asc(nulls_first=True)
        ).values_list('pk', flat=True)[:filter_limit]

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
        Course.objects.dequeue(sis_import)
        if sis_import.is_imported():
            # Decrement the priority
            super(CourseManager, self).get_queryset().filter(
                queue_id=sis_import.pk, priority__gt=Course.PRIORITY_NONE
            ).update(
                queue_id=None, priority=F('priority') - 1)
        else:
            self.queued(sis_import.pk).update(queue_id=None)

        self.purge_expired()

    def purge_expired(self):
        retention_dt = datetime.now(timezone.utc) - timedelta(
            days=getattr(settings, 'COURSE_MODEL_RETENTION_DAYS', 365))
        return super(CourseManager, self).get_queryset().filter(
            priority=Course.PRIORITY_NONE,
            last_modified__lt=retention_dt).delete()


class Course(ImportResource):
    """
    Provisioned Training Course
    """
    training_course = models.ForeignKey(
        TrainingCourse, on_delete=models.CASCADE)
    course_id = models.CharField(
        max_length=80, null=True, db_index=True, unique=True)
    created_date = models.DateTimeField(auto_now=True)
    provisioned_date = models.DateTimeField(null=True)
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

    def json_data(self):
        return {
            "training_course": self.training_course,
            "course_id": self.course_id,
            "term_id": self.term_id,
            "status": self.status,
            "account_id": self.account_id,
            "created_date": localtime(self.deleted_date).isoformat(),
            "provisioned_date": localtime(self.provisioned_date).isoformat() if (
                self.provisioned_date is not None) else None,
            "deleted_date": localtime(self.deleted_date).isoformat() if (
                self.deleted_date is not None) else None,
            "priority": self.PRIORITY_CHOICES[self.priority][1],
            "queue_id": self.queue_id,
        }

    def __str__(self):
        return json.dumps(self.json_data())

    class Meta:
        db_table = 'course'
