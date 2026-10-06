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

        try:
            for imp in Import.objects.find_unposted():
                # SIS post never got a canvas_id back (eg. a timeout), so
                # this import will never be picked up by
                # find_by_requires_update(). Delete it to release its
                # dependent models' queue_id so they can be re-queued.
                logger.warning(
                    f"Clearing unposted import {imp.pk} "
                    f"(post_status={imp.post_status})")
                imp.delete()
        except Exception as err:
            logger.error("{}".format(err))
            raise CommandError(err)
