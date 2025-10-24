# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.conf import settings
from django.core.files.storage import default_storage
from uw_canvas import Canvas
from uw_canvas.accounts import Accounts
from uw_canvas.admins import Admins
from uw_canvas.courses import Courses
from uw_canvas.roles import Roles
from uw_canvas.terms import Terms
from uw_canvas.sis_import import SISImport, CSV_FILES
from uw_canvas.models import SISImport as SISImportModel
from restclients_core.exceptions import DataFailureException
from logging import getLogger
from csv import reader
from io import BytesIO
import zipfile
import json


logger = getLogger(__name__)


def course_names_from_course_sis_id(course_sis_id):
    course = get_course_by_id(course_sis_id)
    return course.name, course.short_name


def get_account_by_id(account_id):
    return Accounts().get_account(account_id)


def get_account_by_sis_id(sis_account_id):
    return Accounts().get_account_by_sis_id(sis_account_id)


def get_sub_accounts(account_id):
    return Accounts(per_page=100).get_sub_accounts(account_id)


def get_all_sub_accounts(account_id):
    return Accounts(per_page=100).get_all_sub_accounts(account_id)


def update_account_sis_id(account_id, sis_account_id):
    return Accounts().update_sis_id(account_id, sis_account_id)


def get_admins(account_id):
    return Admins(per_page=100).get_admins(account_id)


def delete_admin(account_id, user_id, role):
    try:
        ret = Admins().delete_admin(account_id, user_id, role)
    except DataFailureException as err:
        if err.status == 404:  # Non-personal regid?
            return False
        raise
    return ret


def get_course_roles_in_account(account_sis_id):
    if account_sis_id and account_sis_id.startswith('uwcourse:uweo'):
        account_id = getattr(settings, 'CONTINUUM_CANVAS_ACCOUNT_ID')
    else:
        account_id = getattr(settings, 'RESTCLIENTS_CANVAS_ACCOUNT_ID')

    return Roles().get_effective_course_roles_in_account(account_id)


def get_account_role_data(account_id):
    role_data = []
    roles = Roles(per_page=100).get_roles_in_account(account_id)
    for role in sorted(roles, key=lambda r: r.role_id):
        role_data.append(role.json_data())
    return json.dumps(role_data, sort_keys=True)


def get_term_by_sis_id(term_sis_id):
    return Terms().get_term_by_sis_id(term_sis_id)


def get_course_by_id(course_id, params={}):
    return Courses().get_course(course_id, params)


def get_course_by_sis_id(course_sis_id, params={}):
    return Courses().get_course_by_sis_id(course_sis_id, params)


def sis_import_by_path(csv_path, override_sis_stickiness=False):
    dirs, files = default_storage.listdir(csv_path)

    archive = BytesIO()
    zip_file = zipfile.ZipFile(archive, 'w')
    for filename in CSV_FILES:
        if filename in files:
            filepath = csv_path + '/' + filename
            with default_storage.open(filepath, mode='r') as csv:
                zip_file.writestr(filename, csv.read(), zipfile.ZIP_DEFLATED)

    zip_file.close()
    archive.seek(0)

    params = {}
    if override_sis_stickiness:
        params['override_sis_stickiness'] = '1'
        params['clear_sis_stickiness'] = '1'

    return SISImport().import_archive(archive, params=params)


def get_sis_import_status(import_id):
    return SISImport().get_import_status(
        SISImportModel(import_id=str(import_id)))


def delete_sis_import(import_id):
    return SISImport().delete_import(SISImportModel(import_id=str(import_id)))
