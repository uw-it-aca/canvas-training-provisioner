# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.db import models
from training_provisioner.models import Import, ImportResource
import json


class EnrollmentManager(models.Manager):
    def add_enrollments(self, training_course):
        for netid in training_course.get_membership_for_course():
            course_id = training_course.get_course_id_for_member(netid)
            section_id = training_course.get_section_id_for_member(netid)
            enrollment, _ = Enrollment.objects.get_or_create(
                integration_id=netid, course_id=course_id,
                section_id=section_id, defaults={
                    'priority': ImportResource.PRIORITY_DEFAULT
                })

    def queued(self, queue_id):
        return super(EnrollmentManager, self).get_queryset().filter(
            queue_id=queue_id)

    def dequeue(self, sis_import):
        Enrollment.objects.dequeue(sis_import)
        if sis_import.is_imported():
            # Decrement the priority
            super(EnrollmentManager, self).get_queryset().filter(
                queue_id=sis_import.pk, priority__gt=Enrollment.PRIORITY_NONE
            ).update(
                queue_id=None, priority=F('priority') - 1)
        else:
            self.queued(sis_import.pk).update(queue_id=None)

        self.purge_expired()

    def purge_expired(self):
        retention_dt = datetime.now(timezone.utc) - timedelta(
            days=getattr(settings, 'ENROLLMENT_MODEL_RETENTION_DAYS', 365))
        return super(EnrollmentManager, self).get_queryset().filter(
            priority=Enrollment.PRIORITY_NONE,
            last_modified__lt=retention_dt).delete()


class Enrollment(ImportResource):
    """
    Represents a user's Course enrollment event to be processed.
    """
    integration_id = models.CharField(max_length=8)
    course_id = models.CharField(max_length=80)
    section_id = models.CharField(max_length=80, null=True)
    enrollment_datetime = models.DateTimeField(null=True)
    added_date = models.DateTimeField(auto_now=True)
    deleted_date = models.DateTimeField(null=True)
    priority = models.SmallIntegerField(
        default=ImportResource.PRIORITY_DEFAULT,
        choices=ImportResource.PRIORITY_CHOICES)
    queue_id = models.CharField(max_length=30, null=True)

    objects = EnrollmentManager()
    
    def json_data(self):
        return {
            'integration_id': self.integration_id,
            'course_id': self.course_id,
            'section_id': self.section_id,
            'enrollment_datetime': self.enrollment_datetime.isoformat(),
            'deleted_date': (self.deleted_date.isoformat()
                             if self.deleted_date else None),
        }

    def __str__(self):
        return json.dumps(self.json_data())

    class Meta:
        db_table = 'enrollment'
        unique_together = ('integration_id', 'course_id', 'section_id')
