# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from training_provisioner.test import TrainingCourseTestCase
from training_provisioner.models import Import
from training_provisioner.views.api.imports import ImportView, ImportListView
from django.test.client import RequestFactory
from django.urls import reverse_lazy
from django.contrib.auth.models import AnonymousUser
from prometheus_client import REGISTRY
import json


class ImportsAPITest(TrainingCourseTestCase):
    def test_get_imports(self):
        import_list_api = ImportListView()
        url = reverse_lazy('import_list')
        request = RequestFactory().get(url)
        response = import_list_api.get(request)
        imports = json.loads(response.content)

        self.assertEqual(len(imports.get('imports')), 0)

        _ = Import.objects.create(
            csv_type='course', canvas_id='1')

        response = import_list_api.get(request)
        imports = json.loads(response.content)

        self.assertEqual(len(imports.get('imports')), 1)

    def test_get_import(self):
        _ = Import.objects.create(
            csv_type='course', canvas_id='1')

        import_view_api = ImportView()
        url = reverse_lazy('import_view',
                           kwargs={'import_id': '1'})
        request = RequestFactory().get(url)
        response = import_view_api.get(request, import_id='1')
        imports = json.loads(response.content)

        self.assertEqual(imports.get('queue_id'), 1)

    def test_delete_import(self):
        _ = Import.objects.create(
            csv_type='course', canvas_id='1',
            post_status=200, canvas_progress=100)

        import_view_api = ImportView()
        url = reverse_lazy('import_view',
                           kwargs={'import_id': '1'})
        request = RequestFactory().get(url)
        request.user = AnonymousUser()
        response = import_view_api.delete(request, import_id='1')

        self.assertTrue(response.status_code, 204)
        self.assertRaises(
            Import.DoesNotExist,
            Import.objects.get,
            csv_type='course', canvas_id='1')
