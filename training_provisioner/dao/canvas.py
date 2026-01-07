# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.core.files.storage import default_storage
from uw_canvas.courses import Courses
from uw_canvas.sis_import import SISImport, CSV_FILES
from uw_canvas.models import SISImport as SISImportModel
from logging import getLogger
from io import BytesIO
import zipfile
import json


logger = getLogger(__name__)


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
