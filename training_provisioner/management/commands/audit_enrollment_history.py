# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from training_provisioner.models.enrollment import (
    Enrollment, EnrollmentHistoryEvent)
from training_provisioner.models.training_course import TrainingCourse
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = """
    Audit enrollment history completeness by checking that all enrollments
    have appropriate history events and identifying any inconsistencies.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--training-course-id',
            type=int,
            help='Only audit specific training course ID',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output including individual problems',
        )

    def handle(self, *args, **options):
        training_course_id = options.get('training_course_id')
        verbose = options['verbose']

        self.stdout.write("Starting enrollment history audit...")

        # Filter by training course if specified
        if training_course_id:
            try:
                training_course = TrainingCourse.objects.get(
                    id=training_course_id)
                enrollments_query = Enrollment.objects.filter(
                    course__training_course=training_course)
                self.stdout.write(f"Auditing training course: "
                                  f"{training_course.course_name}")
            except TrainingCourse.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Training course {training_course_id} "
                                     f"not found."))
                return
        else:
            enrollments_query = Enrollment.objects.all()
            self.stdout.write("Auditing all enrollments...")

        # Count totals
        total_enrollments = enrollments_query.count()
        total_history_events = EnrollmentHistoryEvent.objects.count()

        self.stdout.write(f"Total enrollments: {total_enrollments}")
        self.stdout.write(f"Total history events: {total_history_events}")

        # Find enrollments without any history
        enrollments_without_history = []
        enrollments_with_missing_created = []
        enrollments_with_inconsistent_state = []

        for enrollment in enrollments_query:
            history_events = EnrollmentHistoryEvent.objects.filter(
                enrollment=enrollment).order_by('timestamp')

            if not history_events.exists():
                enrollments_without_history.append(enrollment)
                continue

            # Check if first event is CREATED
            first_event = history_events.first()
            created_type = EnrollmentHistoryEvent.EVENT_TYPE_CREATED
            if first_event.event_type != created_type:
                enrollments_with_missing_created.append(enrollment)

            # Check for state consistency
            latest_event = history_events.last()

            # Check if deleted status matches history
            has_deletion_event = history_events.filter(
                event_type=EnrollmentHistoryEvent.EVENT_TYPE_DELETED
            ).exists()

            is_currently_deleted = enrollment.deleted_date is not None

            if has_deletion_event != is_currently_deleted:
                enrollments_with_inconsistent_state.append(enrollment)

        # Report findings
        self.stdout.write("\n" + "="*50)
        self.stdout.write("AUDIT RESULTS")
        self.stdout.write("="*50)

        if enrollments_without_history:
            self.stdout.write(
                self.style.WARNING(
                    f"{len(enrollments_without_history)} enrollments "
                    f"have no history events"))
            if verbose:
                for enrollment in enrollments_without_history[:10]:
                    self.stdout.write(f"   - {enrollment.integration_id} in "
                                      f"{enrollment.course.course_id}")
                if len(enrollments_without_history) > 10:
                    remaining = len(enrollments_without_history) - 10
                    self.stdout.write(f"   ... and {remaining} more")
        else:
            self.stdout.write(
                self.style.SUCCESS("✓ All enrollments have history events"))

        if enrollments_with_missing_created:
            self.stdout.write(
                self.style.WARNING(
                    f"{len(enrollments_with_missing_created)} enrollments "
                    f"missing CREATED event"))
            if verbose:
                for enrollment in enrollments_with_missing_created[:10]:
                    self.stdout.write(f"   - {enrollment.integration_id} in "
                                      f"{enrollment.course.course_id}")
        else:
            self.stdout.write(
                self.style.SUCCESS("✓ All enrollments have CREATED events"))

        if enrollments_with_inconsistent_state:
            self.stdout.write(
                self.style.WARNING(
                    f"{len(enrollments_with_inconsistent_state)} "
                    f"enrollments have inconsistent deletion state"))
            if verbose:
                for enrollment in enrollments_with_inconsistent_state[:10]:
                    self.stdout.write(f"   - {enrollment.integration_id} in "
                                      f"{enrollment.course.course_id}")
        else:
            self.stdout.write(
                self.style.SUCCESS("✓ All enrollments have consistent "
                                   "state"))

        # Event type statistics
        event_stats = EnrollmentHistoryEvent.objects.values(
            'event_type').annotate(count=Count('id')).order_by('-count')

        self.stdout.write(f"\nEvent Type Statistics:")
        for stat in event_stats:
            event_type = stat['event_type']
            count = stat['count']
            self.stdout.write(f"  {event_type}: {count}")

        # Summary
        total_issues = (len(enrollments_without_history) +
                        len(enrollments_with_missing_created) +
                        len(enrollments_with_inconsistent_state))

        if total_issues == 0:
            self.stdout.write(
                self.style.SUCCESS(f"Enrollment history audit passed! "
                                   f"No issues found."))
        else:
            self.stdout.write(
                self.style.WARNING(f"Found {total_issues} issues that "
                                   f"may need attention."))
            self.stdout.write(
                "Consider running 'backfill_enrollment_history' to fix "
                "missing history events.")

        self.stdout.write("Audit complete.")
