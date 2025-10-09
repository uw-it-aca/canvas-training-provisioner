# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.db import models
from training_provisioner.models import ImportResource
from datetime import datetime, timezone
from logging import getLogger

logger = getLogger(__name__)


class TermManager(models.Manager):
    def queued(self, queue_id):
        return super().get_queryset().filter(queue_id=queue_id)

    def dequeue(self, sis_import):
        kwargs = {'queue_id': None}
        self.queued(sis_import.pk).update(**kwargs)


class Term(ImportResource):
    """ Represents the provisioned state of courses for a term.
    """
    term_id = models.CharField(max_length=20, unique=True)
    added_date = models.DateTimeField(auto_now_add=True)
    courses_changed_since_date = models.DateTimeField(null=True)
    queue_id = models.CharField(max_length=30, null=True)

    objects = TermManager()

    class Meta:
        db_table = 'term'
