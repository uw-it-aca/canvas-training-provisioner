# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.test import TestCase
from training_provisioner.dao.canvas import *
from unittest.mock import ANY
import mock


class CanvasSISImportsTest(TestCase):
    @mock.patch('training_provisioner.dao.canvas.default_storage.listdir')
    @mock.patch.object(SISImport, 'import_archive')
    def test_sis_import_by_path(self, mock_method, mock_listdir):
        mock_listdir.return_value = ((), ())

        r = sis_import_by_path('abc')
        mock_method.assert_called_with(ANY, params={})

        r = sis_import_by_path('abc', override_sis_stickiness=True)
        mock_method.assert_called_with(
            ANY, params={
                'override_sis_stickiness': '1', 'clear_sis_stickiness': '1'})

    @mock.patch('training_provisioner.dao.canvas.SISImportModel')
    @mock.patch.object(SISImport, 'get_import_status')
    def test_get_sis_import_status(self, mock_method, mock_model):
        r = get_sis_import_status('123')
        mock_model.assert_called_with(import_id='123')

    @mock.patch('training_provisioner.dao.canvas.SISImportModel')
    @mock.patch.object(SISImport, 'delete_import')
    def test_delete_sis_import(self, mock_method, mock_model):
        r = delete_sis_import('123')
        mock_model.assert_called_with(import_id='123')


class CanvasSISImportsTest(TestCase):
    @mock.patch('training_provisioner.dao.canvas.default_storage.listdir')
    @mock.patch.object(SISImport, 'import_archive')
    def test_sis_import_by_path(self, mock_method, mock_listdir):
        mock_listdir.return_value = ((), ())

        r = sis_import_by_path('abc')
        mock_method.assert_called_with(ANY, params={})

        r = sis_import_by_path('abc', override_sis_stickiness=True)
        mock_method.assert_called_with(
            ANY, params={
                'override_sis_stickiness': '1', 'clear_sis_stickiness': '1'})

    @mock.patch('training_provisioner.dao.canvas.SISImportModel')
    @mock.patch.object(SISImport, 'get_import_status')
    def test_get_sis_import_status(self, mock_method, mock_model):
        r = get_sis_import_status('123')
        mock_model.assert_called_with(import_id='123')

    @mock.patch('training_provisioner.dao.canvas.SISImportModel')
    @mock.patch.object(SISImport, 'delete_import')
    def test_delete_sis_import(self, mock_method, mock_model):
        r = delete_sis_import('123')
        mock_model.assert_called_with(import_id='123')


class CanvasAuthSettingsTest(TestCase):
    @mock.patch.object(Accounts, 'get_auth_settings')
    def test_get_auth_settings(self, mock_method):
        auth_settings = get_auth_settings()
        mock_method.assert_called_with('123')

    @mock.patch('uw_canvas.models.CanvasSSOSettings')
    @mock.patch.object(Accounts, 'update_auth_settings')
    def test_get_auth_settings(self, mock_method, mock_model):
        auth_settings = update_auth_settings(mock_model)
        mock_method.assert_called_with('123', mock_model)
