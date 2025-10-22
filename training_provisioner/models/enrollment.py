# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.db import models
from training_provisioner.models import Import, ImportResource
from training_provisioner.exceptions import EnrollmentCourseMismatch
from django.utils.timezone import localtime
import logging
import json


logger = logging.getLogger(__name__)


class EnrollmentManager(models.Manager):
    def add_enrollments(self, training_course):
        enrollments = []
        enrolled_netids = set(self.filter(
            course_id__startswith=training_course.course_id_prefix
        ).values_list('integration_id', flat=True))

        membership = training_course.get_membership_for_course()
        for netid in membership:
            try:
                enrollment = self._add_enrollment(netid, training_course)
                enrollments.append(enrollment)
                enrolled_netids.discard(netid)
            except EnrollmentCourseMismatch as ex:
                logger.error(ex)

        # cull dropped members
        now = localtime()
        for dropped_netid in enrolled_netids:
            try:
                enrollment = Enrollment.objects.get(
                    integration_id=dropped_netid,
                    course_id__startswith=training_course.course_id_prefix)
                enrollment.deleted_date = now
                enrollment.priority = ImportResource.PRIORITY_DEFAULT
                enrollment.save()
                enrollments.append(enrollment)
            except Enrollment.DoesNotExist:
                pass

        return enrollments

    def _add_enrollment(self, netid, training_course):
        try:
            course_id = training_course.get_course_id_for_member(netid)
            section_id = training_course.get_section_id_for_member(netid)
            enrollment = Enrollment.objects.get(
                integration_id=netid,
                course_id__startswith=training_course.course_id_prefix)

            if enrollment.course_id != course_id or (
                    enrollment.section_id != section_id):
                raise EnrollmentCourseMismatch(
                    f"Enrollement for {netid} in "
                    f"{training_course.course_id_prefix} "
                    f"changed from course {enrollment.course_id} "
                    f"to {course_id}, section {enrollment.section_id} "
                    f"to {section_id}: LEAVING UNTOUCHED")

        except Enrollment.DoesNotExist:
            enrollment = Enrollment.objects.create(
                integration_id=netid, course_id=course_id,
                section_id=section_id,
                priority=ImportResource.PRIORITY_DEFAULT)

        return enrollment

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
    integration_id = models.CharField(max_length=8, db_index=True)
    course_id = models.CharField(max_length=80, db_index=True)
    section_id = models.CharField(max_length=80, null=True)
    added_date = models.DateTimeField(auto_now=True)
    enrollment_date = models.DateTimeField(null=True)
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
            'added_date': localtime(self.added_date).isoformat(),
            'enrollment_date': localtime(self.enrollment_date).isoformat() if (
                self.enrollment_date) else None,
            'deleted_date': localtime(self.deleted_date).isoformat() if (
                self.deleted_date) else None,
        }

    def __str__(self):
        return json.dumps(self.json_data())

    class Meta:
        db_table = 'enrollment'
        unique_together = ('integration_id', 'course_id', 'section_id')
