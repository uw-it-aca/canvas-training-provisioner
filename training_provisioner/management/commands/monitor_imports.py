# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.core.management.base import BaseCommand, CommandError
from training_provisioner.models import Import
from logging import getLogger

logger = getLogger(__name__)


class Command(BaseCommand):
    help = "Monitors Canvas Training Course import status."

    def handle(self, *args, **options):
        try:
            for imp in Import.objects.find_by_requires_update():
                imp.update_import_status()
        except Exception as err:
            logger.error("{}".format(err))
            raise CommandError(err)
