# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.conf import settings
from django.core.files.storage import default_storage
from training_provisioner.csv.format import (
    UserHeader, AdminHeader, TermHeader, CourseHeader,
    SectionHeader, EnrollmentHeader, UserCSV,
    AdminCSV, TermCSV, CourseCSV, SectionCSV, EnrollmentCSV)
from datetime import datetime
from logging import getLogger
import os

logger = getLogger(__name__)


class Collector(object):
    def __init__(self):
        self._init_data()

    def _init_data(self):
        self.accounts = []
        self.admins = []
        self.terms = {}
        self.courses = {}
        self.sections = {}
        self.enrollments = []
        self.enrollment_keys = {}
        self.users = {}
        self.headers = {
            'users': UserHeader(),
            'admins': AdminHeader(),
            'terms': TermHeader(),
            'courses': CourseHeader(),
            'sections': SectionHeader(),
            'enrollments': EnrollmentHeader(),
        }

    def add(self, formatter):
        """
        Add the passed csv formatter object based on type, returns True if
        the formatter is added, False otherwise.
        """
        if isinstance(formatter, UserCSV):
            return self._add_user(formatter)
        elif isinstance(formatter, EnrollmentCSV):
            return self._add_enrollment(formatter)
        elif isinstance(formatter, AdminCSV):
            return self._add_admin(formatter)
        elif isinstance(formatter, TermCSV):
            return self._add_term(formatter)
        elif isinstance(formatter, CourseCSV):
            return self._add_course(formatter)
        elif isinstance(formatter, SectionCSV):
            return self._add_section(formatter)
        else:
            raise TypeError(
                'Unknown CSVFormat class: {}'.format(type(formatter)))

    def _add_admin(self, formatter):
        self.admins.append(formatter)
        return True

    def _add_user(self, formatter):
        if formatter.key not in self.users:
            self.users[formatter.key] = formatter
            return True
        return False

    def _add_term(self, formatter):
        if formatter.key not in self.terms:
            self.terms[formatter.key] = formatter
            return True
        return False

    def _add_course(self, formatter):
        if formatter.key not in self.courses:
            self.courses[formatter.key] = formatter
            return True
        return False

    def _add_section(self, formatter):
        if formatter.key not in self.sections:
            self.sections[formatter.key] = formatter
            return True
        return False

    def _add_enrollment(self, formatter):
        if formatter.key not in self.enrollment_keys:
            self.enrollment_keys[formatter.key] = True
            self.enrollments.append(formatter)
            return True
        return False

    def has_data(self):
        """
        Returns True if the collector contains data, False otherwise.
        """
        for csv_type in self.headers:
            if len(getattr(self, csv_type)):
                return True
        return False

    def write_files(self):
        """
        Writes all csv files. Returns a path to the csv files, or None
        if no data was written.
        """
        filepath = None
        if self.has_data():
            filepath = datetime.now().strftime('%Y/%m/%d/%H%M%S-%f')
            for csv_type in self.headers:
                try:
                    data = list(getattr(self, csv_type).values())
                    data.sort()
                except AttributeError:
                    data = getattr(self, csv_type)

                if len(data):
                    os.makedirs(os.path.join(
                        settings.MEDIA_ROOT, filepath), exist_ok=True)
                    filename = os.path.join(filepath, csv_type + '.csv')
                    with default_storage.open(filename, mode='w') as f:
                        headers = self.headers[csv_type]
                        f.write(str(headers))
                        for line in data:
                            f.write(str(line))

            self._init_data()

        if getattr(settings, 'TRAINING_IMPORT_CSV_DEBUG', False):
            logger.debug('CSV PATH: {}'.format(filepath))
            return None
        else:
            return filepath
