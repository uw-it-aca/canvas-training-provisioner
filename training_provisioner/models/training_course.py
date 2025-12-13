# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.timezone import localtime
from training_provisioner.dao.membership import (
    test_membership, title_vi_membership_candidates,
    title_vi_booster_membership_candidates)
from importlib import import_module
import logging


logger = logging.getLogger(__name__)


class TrainingCourseManager(models.Manager):
    def active_courses(self, term_id=None):
        filter = {
            'is_provisioned': True,
            'deleted_date__isnull': True
        }

        if term_id:
            filter['term_id'] = term_id

        return self.filter(**filter)

    def load_active_courses(self):
        for training_course in self.active_courses():
            logger.info(
                "Loading training course "
                f"{training_course.blueprint_course_id} "
                f"for term {training_course.term_id}")

            training_course.load_courses_and_enrollments()


class TrainingCourse(models.Model):
    """
    Represents a training course and necessary provisioning parameters.
    """
    TEST_MEMBERS = 0
    TITLE_VI_MEMBERS = 1
    TITLE_VI_BOOSTER_MEMBERS = 2
    MEMBERSHIP_CHOICES = (
        (TEST_MEMBERS, 'test_membership'),
        (TITLE_VI_MEMBERS, 'title_vi_membership_candidates'),
        (TITLE_VI_BOOSTER_MEMBERS, 'title_vi_booster_membership_candidates'),
    )

    COURSE_MODEL = ('training_provisioner.models.course', 'Course')
    COURSE_MODELS = (
        COURSE_MODEL,
        ('training_provisioner.models.section', 'Section'),
        ('training_provisioner.models.enrollment', 'Enrollment'),
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
    COURSE_TYPE_101 = '101'
    COURSE_TYPE_BOOSTER = 'booster'
    COURSE_TYPE_CHOICES = (
          (COURSE_TYPE_101, 'Title VI 101 Course'),
          (COURSE_TYPE_BOOSTER, 'Title VI Booster Course'),
    )

    course_name = models.CharField(max_length=200)
    blueprint_course_id = models.CharField(max_length=100)
    term_id = models.CharField(max_length=30, db_index=True)
    account_id = models.CharField(max_length=80)
    membership_type = models.SmallIntegerField(
        default=TEST_MEMBERS,
        choices=MEMBERSHIP_CHOICES)
    course_status = models.SmallIntegerField(
        default=COURSE_STATUS_ACTIVE,
        choices=COURSE_STATUS_CHOICES)
    course_type = models.CharField(
        max_length=50,
        choices=COURSE_TYPE_CHOICES,
        default=COURSE_TYPE_101)
    is_provisioned = models.BooleanField(default=False)
    course_count = models.IntegerField(
        default=1, validators=[MinValueValidator(1)])
    section_count = models.IntegerField(
        default=0, validators=[MinValueValidator(0)])
    creation_date = models.DateTimeField(auto_now=True)
    deleted_date = models.DateTimeField(null=True, blank=True)

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

    def save(self, force_update=False, *args, **kwargs):
        """
        re-prioritize course import on change leaving it to the
        admin interface to prevent read-only value changes
        """
        if self.pk:
            model = self._dependent_model(*self.COURSE_MODEL)
            model.objects.get_models_for_training_course(self).update(
                priority=model.PRIORITY_DEFAULT)

        super().save(force_update, *args, **kwargs)

    def course_id(self, index):
        ordinal = index + 1
        return f"{self.course_id_prefix}{ordinal:03d}"

    def get_course_membership(self) -> list[str]:
        # Call the appropriate membership function from dao.membership
        # based on membership choice type
        try:
            return eval(f"{self.get_membership_type_display()}(self)")
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
        # Entrypoint for loading jobs for sections, enrollments
        for model in self._dependent_models():
            model.objects.add_models_for_training_course(self)

    def _dependent_models(self):
        for course_model in self.COURSE_MODELS:
            yield self._dependent_model(*course_model)

    def _dependent_model(self, module_name, model_name):
        return getattr(import_module(module_name), model_name)

    def json_data(self):
        return {
            "course_name": self.course_name,
            "blueprint_course_id": self.blueprint_course_id,
            "term_id": self.term_id,
            "account_id": self.account_id,
            "membership_type": self.get_membership_type_display(),
            "course_type": self.get_course_type_display(),
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
        return (f"{self.course_name} "
                f"({self.blueprint_course_id} - {self.term_id})")

    class Meta:
        db_table = 'training_course'
        unique_together = ('blueprint_course_id', 'term_id')
