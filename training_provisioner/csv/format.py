# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


#from training_provisioner.dao.account import account_name


# from sis_provisioner.dao.term import (
#     term_sis_id, term_name, term_start_date, term_end_date, course_end_date)
# from sis_provisioner.dao.course import (
#     is_active_section, section_short_name, section_long_name)
# from sis_provisioner.dao.user import (
#     user_sis_id, user_integration_id, user_email, user_fullname)
import csv
import io


class CSVFormat(object):
    def __init__(self, course):
        self.key = None
        self.data = []

    def __lt__(self, other):
        return self.key < other.key

    def __eq__(self, other):
        return self.key == other.key

    def __str__(self):
        """
        Creates a line of csv data from the obj data attribute
        """
        csv.register_dialect('unix_newline', lineterminator='\n')

        s = io.BytesIO()
        try:
            csv.writer(s, dialect='unix_newline').writerow(self.data)
        except TypeError:
            s = io.StringIO()
            csv.writer(s, dialect='unix_newline').writerow(self.data)

        line = s.getvalue()
        s.close()
        return line


# CSV Header classes
class UserHeader(CSVFormat):
    def __init__(self):
        self.data = ['user_id', 'integration_id', 'login_id', 'full_name',
                     'sortable_name', 'short_name', 'email', 'status']


class AdminHeader(CSVFormat):
    def __init__(self):
        self.data = ['user_id', 'account_id', 'role', 'status']


class TermHeader(CSVFormat):
    def __init__(self):
        self.data = ['term_id', 'name', 'status']


class CourseHeader(CSVFormat):
    def __init__(self):
        self.data = ['course_id', 'short_name', 'long_name', 'account_id',
                     'term_id', 'status', 'blueprint_course_id']


class SectionHeader(CSVFormat):
    def __init__(self):
        self.data = ['section_id', 'course_id', 'name', 'status']


class EnrollmentHeader(CSVFormat):
    def __init__(self):
        self.data = ['course_id', 'user_integration_id', 'role',
                     'role_id', 'section_id', 'status']


# CSV Data classes
class UserCSV(CSVFormat):
    """
    user_id, integration_id, login_id, full_name, sortable_name, short_name,
    email, status (active|deleted)
    """
    def __init__(self, user, status='active'):
        self.key = user_sis_id(user)
        firstname, lastname = user_fullname(user)
        if firstname and lastname:
            full_name = f'{firstname} {lastname}'
            sortable_name = f'{lastname}, {firstname}'
        else:
            full_name = firstname or lastname
            sortable_name = firstname or lastname

        self.data = [
            self.key,
            user_integration_id(user),
            user.uwnetid if hasattr(user, 'uwnetid') else user.login_id,
            full_name, sortable_name, full_name,
            user_email(user),
            status]


class AdminCSV(CSVFormat):
    """
    user_id, account_id, role, status (active|deleted)
    """
    def __init__(self, user_id, account_id, role, status='active'):
        self.data = [user_id, account_id, role, status]


class TermCSV(CSVFormat):
    """
    term_id, name, status (active|deleted), start_date, end_date
    """
    def __init__(self, section, status='active'):
        self.key = term_sis_id(section)
        self.data = [self.key,
                     term_name(section),
                     status]


class CourseCSV(CSVFormat):
    """
    course_id, short_name, long_name, account_id,
    term_id, status, blueprint_course_id
    """
    def __init__(self, **kwargs):
        self.key = kwargs['course_id']
        self.data = [self.key, kwargs['short_name'], kwargs['long_name'],
                     kwargs['account_id'], kwargs['term_id'],
                     kwargs.get('status', 'active'),
                     kwargs.get('blueprint_course_id')]


class SectionCSV(CSVFormat):
    """
    section_id, course_id, name, status (active|deleted)
    """
    def __init__(self, **kwargs):
        self.key = kwargs['section_id']
        self.data = [self.key, kwargs['course_id'], kwargs['name'],
                     kwargs.get('status', 'active')]


class EnrollmentCSV(CSVFormat):
    """
    course_id, root_account, user_id, role, role_id, section_id,
    status (active|inactive|deleted|completed), associated_user_id
    """
    def __init__(self, **kwargs):
        course_id = None if (
            kwargs.get('section_id')) else kwargs.get('course_id')
        section_id = kwargs.get('section_id')
        person = registration.person
        role = 'student'
        status = 'active'

        self.key = "{}:{}:{}:{}:{}".format(
            course_id, section_id, user_id, role, status)
        self.data = [course_id, None, user_id, role, None, section_id, status,
                     None]
