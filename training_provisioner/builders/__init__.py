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

    def add_student_enrollment_data(self, registration):
        """
        Generates one student enrollment for the passed registration.
        """
        if self.add_user_data_for_person(registration.person):
            self.data.add(EnrollmentCSV(registration=registration))

    def add_group_enrollment_data(self, login_id, section_id, role, status):
        """
        Generates one enrollment for the passed group member.
        """
        try:
            person = get_person_by_netid(login_id)
            if self.add_user_data_for_person(person):
                self.data.add(EnrollmentCSV(
                    section_id=section_id, person=person, role=role,
                    status=status))

        except InvalidLoginIdException as ex:
            self.logger.info("Skip group member {}: {}".format(
                login_id, ex))
