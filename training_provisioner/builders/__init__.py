# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from training_provisioner.csv.data import Collector
from training_provisioner.csv.format import EnrollmentCSV
from restclients_core.exceptions import DataFailureException
from logging import getLogger


class Builder(object):
    def __init__(self, items=[]):
        self.data = Collector()
        self.queue_id = None
        self.invalid_users = {}
        self.items = items
        self.logger = getLogger(__name__)

    def _init_build(self, **kwargs):
        return

    def _process(self, item):
        raise NotImplementedError

    def _write(self):
        return self.data.write_files()

    def build(self, **kwargs):
        self._init_build(**kwargs)
        for item in self.items:
            self._process(item)
        return self._write()
