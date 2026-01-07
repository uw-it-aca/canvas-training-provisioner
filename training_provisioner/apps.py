# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.apps import AppConfig
from restclients_core.dao import MockDAO
import os


class TrainingProvisionerConfig(AppConfig):
    name = 'training_provisioner'

    def ready(self):
        mock_training_data = os.path.join(
            os.path.dirname(__file__), "resources")
        MockDAO.register_mock_path(mock_training_data)
