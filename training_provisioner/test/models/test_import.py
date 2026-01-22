# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from training_provisioner.test import TrainingCourseTestCase
from training_provisioner.models import Import
from django.test import override_settings
from prometheus_client import REGISTRY


class ImportsAPITest(TrainingCourseTestCase):
    @override_settings(RESTCLIENTS_CANVAS_ACCOUNT_ID='12345')
    def test_import_metrics(self):
        import_model = Import.objects.create(
            csv_type='course', canvas_id='1')

        warn_before = REGISTRY.get_sample_value(
            'studenttraining_import_warnings_total')
        error_before = REGISTRY.get_sample_value(
            'studenttraining_import_errors_total')

        import_model.update_import_status()

        warn_after = REGISTRY.get_sample_value(
            'studenttraining_import_warnings_total')
        error_after = REGISTRY.get_sample_value(
            'studenttraining_import_errors_total')

        self.assertEqual(1, warn_after - warn_before)
        self.assertEqual(1, error_after - error_before)
