# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from training_provisioner.models.enrollment import (
    Enrollment, EnrollmentHistoryEvent)
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """
    Backfill enrollment history for existing enrollments that don't have
    history events. This creates CREATED events for enrollments that exist
    but don't have any history tracked.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--course-id',
            type=str,
            help='Only backfill history for specific course ID',
        )
        parser.add_argument(
            '--training-course-id',
            type=int,
            help='Only backfill history for specific training course ID',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        course_id = options.get('course_id')
        training_course_id = options.get('training_course_id')

        # Build queryset of enrollments without history
        enrollments_query = Enrollment.objects.all()

        if course_id:
            enrollments_query = enrollments_query.filter(
                course__course_id=course_id)

        if training_course_id:
            enrollments_query = enrollments_query.filter(
                course__training_course_id=training_course_id)

        # Find enrollments that don't have any history events
        enrollments_without_history = []
        for enrollment in enrollments_query:
            if not EnrollmentHistoryEvent.objects.filter(
                    enrollment=enrollment).exists():
                enrollments_without_history.append(enrollment)

        count = len(enrollments_without_history)

        if count == 0:
            self.stdout.write(
                self.style.SUCCESS("No enrollments need history "
                                   "backfilling."))
            return

        self.stdout.write(f"Found {count} enrollments without history "
                          f"events.")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"DRY RUN: Would create {count} history "
                                   f"events for existing enrollments."))

            # Show first 10 enrollments
            for enrollment in enrollments_without_history[:10]:
                self.stdout.write(f"  - {enrollment.integration_id} in "
                                  f"{enrollment.course.course_id}")

            if count > 10:
                self.stdout.write(f"  ... and {count - 10} more")
            return

        # Create history events for enrollments without history
        created_count = 0
        for enrollment in enrollments_without_history:
            try:
                # Create a CREATED event with the enrollment's current state
                # Use created_date as timestamp if available, otherwise now
                timestamp = enrollment.created_date or timezone.now()

                EnrollmentHistoryEvent.objects.create(
                    enrollment=enrollment,
                    event_type=EnrollmentHistoryEvent.EVENT_TYPE_CREATED,
                    integration_id=enrollment.integration_id,
                    course_id=enrollment.course.course_id,
                    section_id=(enrollment.section.section_id
                                if enrollment.section else None),
                    eligible_terms=(enrollment.eligible_terms.copy()
                                    if enrollment.eligible_terms else []),
                    timestamp=timestamp
                )
                created_count += 1

                if created_count % 100 == 0:
                    self.stdout.write(f"Processed {created_count}/{count}...")

            except Exception as e:
                logger.error(f"Failed to create history for enrollment "
                             f"{enrollment.id}: {e}")
                self.stdout.write(
                    self.style.ERROR(f"Error processing enrollment "
                                     f"{enrollment.integration_id}: {e}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {created_count} history events "
                f"for existing enrollments."))
