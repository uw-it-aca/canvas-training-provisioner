# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.core.management.base import BaseCommand
from django.utils.timezone import localtime
from training_provisioner.models import Import


class Command(BaseCommand):
    help = "Show recent Canvas SIS imports with errors or warnings."

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit', type=int, default=20,
            help='Number of imports to show (default: 20)')
        parser.add_argument(
            '--type', type=str, choices=['course', 'section', 'enrollment'],
            help='Filter by CSV type')
        parser.add_argument(
            '--all', action='store_true',
            help='Show all imports, not just those with errors or warnings')

    def handle(self, *args, **options):
        qs = Import.objects.order_by('-added_date')

        if options['type']:
            qs = qs.filter(csv_type=options['type'])

        if not options['all']:
            from django.db.models import Q
            qs = qs.filter(
                Q(csv_errors__isnull=False) |
                Q(canvas_errors__isnull=False) |
                Q(canvas_warnings__isnull=False) |
                Q(post_status__isnull=False, post_status__gt=200)
            )

        imports = qs[:options['limit']]

        if not imports:
            self.stdout.write(self.style.SUCCESS("No imports with errors found."))
            return

        for imp in imports:
            added = localtime(imp.added_date).strftime('%Y-%m-%d %H:%M:%S')
            self.stdout.write(
                f"\n[{added}] Import #{imp.pk} "
                f"type={imp.csv_type} "
                f"post_status={imp.post_status} "
                f"monitor_status={imp.monitor_status} "
                f"canvas_id={imp.canvas_id} "
                f"state={imp.canvas_state}"
            )
            self.stdout.write(f"  path: {imp.csv_path}")

            if imp.csv_errors:
                self.stdout.write(self.style.ERROR("  csv_errors:"))
                for line in imp.csv_errors.strip().splitlines():
                    self.stdout.write(f"    {line}")

            if imp.canvas_errors:
                self.stdout.write(self.style.ERROR("  canvas_errors:"))
                for line in str(imp.canvas_errors).strip().splitlines():
                    self.stdout.write(f"    {line}")

            if imp.canvas_warnings:
                self.stdout.write(self.style.WARNING("  canvas_warnings:"))
                for line in str(imp.canvas_warnings).strip().splitlines():
                    self.stdout.write(f"    {line}")
