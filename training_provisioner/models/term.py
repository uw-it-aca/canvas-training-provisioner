# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.db import models
from training_provisioner.models import ImportResource
from datetime import datetime, timezone
import re
from logging import getLogger


logger = getLogger(__name__)


class TermManager(models.Manager):
    def add_term(self, term_id):
        if not self._valid_term(term_id):
            raise ValueError(f"Invalid term_id: {term_id}")

        term, _ = Term.objects.get_or_create(term_id=term_id)

    def _valid_term(self, term_id):
        import pdb; pdb.set_trace()
        return re.match(r'^20\d{2}\-20\d{2}$', term_id) is not None

    def queued(self, queue_id):
        return super().get_queryset().filter(queue_id=queue_id)

    def dequeue(self, sis_import):
        kwargs = {'queue_id': None}
        self.queued(sis_import.pk).update(**kwargs)


class Term(ImportResource):
    """
    Represents the provisioned state of a term.
    """
    term_id = models.CharField(max_length=20, unique=True)
    added_date = models.DateTimeField(auto_now_add=True)
    queue_id = models.CharField(max_length=30, null=True)

    objects = TermManager()

    def __str__(self):
        return f"Term {self.term_id}"

    class Meta:
        db_table = 'term'
