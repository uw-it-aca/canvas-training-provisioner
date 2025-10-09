# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.db import models
from training_provisioner.models.enrollment import Enrollment
from training_provisioner.dao.membership import get_title_vi_membership
from django.utils.timezone import localtime
import json


class TrainingCourseManager(models.Manager):
    def active_courses(self):
        return self.filter(is_provisioned=True, deleted_date__isnull=True)


class TrainingCourse(models.Model):
    """
    Represents a training course and necessary provisioning parameters.
    """
    MEMBERSHIP_TITLE_VI = 0
    MEMBERSHIP_CHOICES = (
        (MEMBERSHIP_TITLE_VI, 'title_vi'),
    )

    COURSE_STATUS_ACTIVE = 0
    COURSE_STATUS_DELETED = 1
    COURSE_STATUS_COMPLETED = 2
    COURSE_STATUS_PUBLISHED = 3
    COURSE_STATUS_CHOICES = (
        (COURSE_STATUS_ACTIVE, 'active'),
        (COURSE_STATUS_DELETED, 'deleted'),
        (COURSE_STATUS_COMPLETED, 'completed'),
        (COURSE_STATUS_PUBLISHED, 'published'),
    )

    blueprint_course_id = models.CharField(
        max_length=80, null=True, db_index=True)
    term_id = models.CharField(max_length=30, db_index=True)
    account_id = models.CharField(max_length=80, null=True)
    membership_type = models.SmallIntegerField(
        default=MEMBERSHIP_TITLE_VI,
        choices=MEMBERSHIP_CHOICES)
    course_status = models.SmallIntegerField(
        default=COURSE_STATUS_ACTIVE,
        choices=COURSE_STATUS_CHOICES)
    sis_import_prefix = models.CharField(max_length=255, unique=True)
    is_provisioned = models.BooleanField(default=False)
    course_count = models.IntegerField(default=0)
    section_count = models.IntegerField(default=0)
    creation_date = models.DateTimeField(auto_now=True)
    deleted_date = models.DateTimeField(null=True)

    objects = TrainingCourseManager()

    @property
    def course_status_name(self):
        return self.COURSE_STATUS_CHOICES[self.course_status][1]

    @property
    def course_id_prefix(self):
        return f"{self.sis_import_prefix}-{self.term_id}"

    def get_membership_for_course(self):
        if self.membership_type == self.MEMBERSHIP_TITLE_VI:
            return get_title_vi_membership()

        raise ValueError("Invalid membership type")

    def get_all_course_sis_import_ids(self):
        return [
            f"{self.course_id_prefix}-{i}" for i in range(self.course_count)]

    def get_course_id_for_member(self, integration_id):
        return (f"{self.course_id_prefix}-"
                f"{self.course_copy_for_member(integration_id)}")

    def course_copy_for_member(self, integration_id):
        """
        Which of the self.course_count courses to use for
        member with integration_id
        """
        return int(integration_id) % self.course_count

    def json_data(self):
        return {
            "blueprint_course_id": self.blueprint_course_id,
            "term_id": self.term_id,
            "account_id": self.account_id,
            "membership_type": self.MEMBERSHIP_CHOICES[
                self.membership_type][1],
            "course_status": self.course_status,
            "course_status_name": self.course_status_name,
            "sis_import_prefix": self.sis_import_prefix,
            "course_count": self.course_count,
            "section_count": self.section_count,
            "creation_date": localtime(self.creation_date).isoformat() if (
                self.creation_date is not None) else None,
            "deleted_date": localtime(self.deleted_date).isoformat() if (
                self.deleted_date is not None) else None
        }

    def __str__(self):
        return json.dumps(self.json_data())

    class Meta:
        db_table = 'training_course'
