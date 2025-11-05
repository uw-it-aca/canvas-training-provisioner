# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.db import models
from training_provisioner.dao.membership import (
    get_test_membership, get_title_vi_membership)
from django.utils.timezone import localtime
from importlib import import_module
import json


class TrainingCourseManager(models.Manager):
    def active_courses(self, term_id=None):
        filter = {
            'is_provisioned': True,
            'deleted_date__isnull': True
        }

        if term_id:
            filter['term_id'] = term_id

        return self.filter(**filter)


class TrainingCourse(models.Model):
    """
    Represents a training course and necessary provisioning parameters.
    """
    MEMBERSHIP_TEST_MEMBERS = 0
    MEMBERSHIP_TITLE_VI = 1
    MEMBERSHIP_CHOICES = (
        (MEMBERSHIP_TEST_MEMBERS, 'get_test_membership'),
        (MEMBERSHIP_TITLE_VI, 'get_title_vi_membership'),
    )

    COURSE_MODELS = (
        'training_provisioner.models.course.Course',
        'training_provisioner.models.section.Section',
        'training_provisioner.models.enrollment.Enrollment'
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

    blueprint_course_id = models.CharField(max_length=100)
    term_id = models.CharField(max_length=30, db_index=True)
    account_id = models.CharField(max_length=80)
    membership_type = models.SmallIntegerField(
        default=MEMBERSHIP_TITLE_VI,
        choices=MEMBERSHIP_CHOICES)
    course_status = models.SmallIntegerField(
        default=COURSE_STATUS_ACTIVE,
        choices=COURSE_STATUS_CHOICES)
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
        return f"{self.term_id}-{self.blueprint_course_id}-"

    @property
    def course_import_ids(self):
        return [f"{self.course_id(i)}" for i in range(self.course_count)]

    def course_id(self, index):
        ordinal = index + 1
        return f"{self.course_id_prefix}{ordinal}"

    def get_membership_for_course(self):
        try:
            fff = self.get_membership_type_display()
            return eval(f"{fff}()")
        except Exception as ex:
            raise ValueError(f"Invalid membership: {ex}")

    def get_course_id_for_member(self, integration_id):
        return self.course_id(self._course_index_for_member(integration_id))

    def _course_index_for_member(self, integration_id):
        """
        Which of the self.course_count courses the
        member with integration_id is enrolled
        """
        return self._hash(integration_id) % self.course_count

    def _hash(self, integration_id):
        """
        integration_ids are UW Student numbers. no complex hash req'd
        """
        return int(integration_id)

    def load_courses_and_enrollments(self):
        for model_cls in self.COURSE_MODELS:
            modname, _, clsname = model_cls.rpartition('.')
            module = import_module(modname)
            model = getattr(module, clsname)
            model.objects.add_models_for_training_course(self)

    def json_data(self):
        return {
            "blueprint_course_id": self.blueprint_course_id,
            "term_id": self.term_id,
            "account_id": self.account_id,
            "membership_type": self.MEMBERSHIP_CHOICES[
                self.membership_type][1],
            "course_status": self.course_status,
            "course_status_name": self.course_status_name,
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
        unique_together = ('blueprint_course_id', 'term_id')
