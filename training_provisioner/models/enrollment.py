# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.db import models
from training_provisioner.models import Import, ImportResource
from training_provisioner.models.course import Course
from training_provisioner.models.section import Section
from training_provisioner.exceptions import (
    MissingCourseException, MissingSectionException, EnrollmentCourseMismatch)
from django.utils.timezone import localtime
import logging
import json


logger = logging.getLogger(__name__)


class EnrollmentManager(models.Manager):
    def add_enrollments(self, training_course):
        enrollments = []
        enrolled_netids = set(self.filter(
            course__training_course=training_course
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
                    course__training_course=training_course)
                enrollment.deleted_date = now
                enrollment.priority = ImportResource.PRIORITY_DEFAULT
                enrollment.save()
                enrollments.append(enrollment)
                drop_id = enrollment.section.section_id if (
                    enrollment.section) else enrollment.course.course_id
                logger.info(f"delete enrollment {dropped_netid} "
                            f"from {drop_id}")

            except Enrollment.DoesNotExist:
                pass

        return enrollments

    def _add_enrollment(self, netid, training_course):
        try:
            course_id = training_course.get_course_id_for_member(netid)
            course = Course.objects.get(course_id=course_id)
            section_id = course.get_section_id_for_member(netid)
            section = Section.objects.get(section_id=section_id) if (
                section_id is not None) else None
            priority = Enrollment.PRIORITY_DEFAULT

            enrollment = Enrollment.objects.get(
                integration_id=netid, course__training_course=training_course)

            if not (enrollment.course == course
                        and enrollment.section == section):
                orig_course_id = enrollment.course.course_id
                orig_section_id = enrollment.section.section_id if (
                    enrollment.section) else "None"
                raise EnrollmentCourseMismatch(
                    f"Enrollment for {netid} in "
                    f"{training_course.course_id_prefix} CHANGED: course from "
                    f"{orig_course_id} to {course_id}, section from "
                    f"{orig_section_id} to {section_id}: enrollment unchanged")

        except Course.DoesNotExist:
            raise MissingCourseException(
                f"Enrollment for {netid} in "
                f"{training_course.course_id_prefix} missing course model "
                f"for: {course_id}")
        except Section.DoesNotExist:
            raise MissingSectionException(
                f"Enrollment for {netid} in "
                f"{training_course.course_id_prefix} missing section model "
                f"for: {section_id}")
        except Enrollment.DoesNotExist:
            enrollment = Enrollment.objects.create(
                integration_id=netid, course=course, section=section)
            logger.info(f"create enrollment {netid} in "
                         f"{section_id if section_id else course_id}")

        return enrollment

    def course_imports(self, course):
        pks = super(EnrollmentManager, self).get_queryset().filter(
            course=course.id,
            priority__gt=ImportResource.PRIORITY_NONE,
            queue_id__isnull=True
        ).values_list('pk', flat=True)

        super(EnrollmentManager, self).get_queryset().filter(
            pk__in=list(pks)).update(queue_id=course.queue_id)

        return super(EnrollmentManager, self).get_queryset().filter(
            pk__in=list(pks))

    def queued(self, queue_id):
        return super(EnrollmentManager, self).get_queryset().filter(
            queue_id=queue_id)

    def dequeue(self, sis_import):
        if sis_import.is_imported():
            # Decrement the priority
            super(EnrollmentManager, self).get_queryset().filter(
                queue_id=sis_import.pk, priority__gt=Enrollment.PRIORITY_NONE
            ).update(
                queue_id=None, priority=F('priority') - 1)
        else:
            self.queued(sis_import.pk).update(queue_id=None)


class Enrollment(ImportResource):
    """
    Represents a user's Course enrollment event to be processed.
    """
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, null=True, on_delete=models.CASCADE)
    integration_id = models.CharField(max_length=8, db_index=True)
    created_date = models.DateTimeField(auto_now=True)
    provisioned_date = models.DateTimeField(null=True)
    deleted_date = models.DateTimeField(null=True)
    priority = models.SmallIntegerField(
        default=ImportResource.PRIORITY_DEFAULT,
        choices=ImportResource.PRIORITY_CHOICES)
    queue_id = models.CharField(max_length=30, null=True)

    objects = EnrollmentManager()
    
    def json_data(self):
        return {
            'course': self.course.json_data() if self.course else None,
            'section': self.section.json_data() if self.section else None,
            'integration_id': self.integration_id,
            'created_date': localtime(self.created_date).isoformat(),
            'provisioned_date': localtime(self.provisioned_date).isoformat() if (
                self.provisioned_date) else None,
            'deleted_date': localtime(self.deleted_date).isoformat() if (
                self.deleted_date) else None,
        }

    def __str__(self):
        return json.dumps(self.json_data())

    class Meta:
        db_table = 'enrollment'
        unique_together = ('integration_id', 'course', 'section')
