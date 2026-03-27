# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.core.management.base import BaseCommand
from training_provisioner.dao.canvas import (
    get_auth_settings, update_auth_settings)
import logging


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Update URLs for test canvas student training instances"
    TEST_DISCOVERY_URL = (
        "https://test-login.canvas.uw.edu/student-training-login")

    def handle(self, *args, **options):
        auth_settings = get_auth_settings()
        if auth_settings.auth_discovery_url != self.TEST_DISCOVERY_URL:
            logger.info(f"Update discovery url "
                        f"({auth_settings.auth_discovery_url}) to "
                        f"{self.TEST_DISCOVERY_URL}")
            auth_settings.auth_discovery_url = self.TEST_DISCOVERY_URL
            try:
                update_auth_settings(auth_settings)
            except Exception as ex:
                logger.error(f"Discovery url update failed: {ex}")
