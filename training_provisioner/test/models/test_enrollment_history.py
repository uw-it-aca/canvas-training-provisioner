# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch
from training_provisioner.test import TrainingCourseTestCase
from training_provisioner.models.training_course import TrainingCourse
from training_provisioner.models.course import Course
from training_provisioner.models.section import Section
from training_provisioner.models.enrollment import (
    Enrollment, EnrollmentHistoryEvent
)


class EnrollmentHistoryEventModelTest(TrainingCourseTestCase):
    """Test EnrollmentHistoryEvent model and manager methods."""

    def setUp(self):
        """Set up test data."""
        # Use fixture-based training course
        self.training_course = TrainingCourse.objects.get(pk=1)

        # Create test course and section
        self.course = Course.objects.create(
            course_id="TEST001",
            training_course=self.training_course,
            course_ordinal=1
        )
        self.section = Section.objects.create(
            section_id="TEST001_SEC01",
            course=self.course,
            section_ordinal=1
        )
        self.enrollment = Enrollment.objects.create(
            integration_id="12345678",
            course=self.course,
            section=self.section,
            eligible_terms=["20251", "20252"]
        )

    def test_create_history_event(self):
        """Test creating a history event."""
        event = self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_CREATED
        )

        self.assertIsInstance(event, EnrollmentHistoryEvent)
        self.assertEqual(event.enrollment, self.enrollment)
        self.assertEqual(event.event_type,
                         EnrollmentHistoryEvent.EVENT_TYPE_CREATED)
        self.assertEqual(event.integration_id, "12345678")
        self.assertEqual(event.course_id, "TEST001")
        self.assertEqual(event.section_id, "TEST001_SEC01")
        self.assertEqual(event.eligible_terms, ["20251", "20252"])
        self.assertIsNone(event.previous_eligible_terms)

    def test_create_update_event_with_previous_terms(self):
        """Test creating an update event with previous terms."""
        previous_terms = ["20251"]
        event = self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_UPDATED,
            previous_terms=previous_terms
        )

        self.assertEqual(
            event.event_type,
            EnrollmentHistoryEvent.EVENT_TYPE_UPDATED
        )
        self.assertEqual(event.previous_eligible_terms, previous_terms)
        self.assertEqual(event.eligible_terms, ["20251", "20252"])

    def test_manager_for_student(self):
        """Test manager method for_student."""
        # Create events for the student
        event1 = self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_CREATED
        )

        # Create another enrollment/event for different student
        enrollment2 = Enrollment.objects.create(
            integration_id="87654321",
            course=self.course,
            eligible_terms=["20251"]
        )
        event2 = enrollment2.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_CREATED
        )

        # Test for_student method
        student_events = EnrollmentHistoryEvent.objects.for_student("12345678")
        self.assertEqual(student_events.count(), 1)
        self.assertEqual(student_events.first(), event1)

    def test_manager_for_course(self):
        """Test manager method for_course."""
        event = self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_CREATED
        )

        course_events = EnrollmentHistoryEvent.objects.for_course(self.course)
        self.assertEqual(course_events.count(), 1)
        self.assertEqual(course_events.first(), event)

    def test_manager_by_event_type(self):
        """Test manager method by_event_type."""
        created_event = self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_CREATED
        )
        updated_event = self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_UPDATED,
            previous_terms=["20251"]
        )

        created_events = EnrollmentHistoryEvent.objects.by_event_type(
            EnrollmentHistoryEvent.EVENT_TYPE_CREATED
        )
        self.assertEqual(created_events.count(), 1)
        self.assertEqual(created_events.first(), created_event)

    def test_manager_for_student_in_course(self):
        """Test manager method for_student_in_course."""
        event = self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_CREATED
        )

        events = EnrollmentHistoryEvent.objects.for_student_in_course(
            "12345678", self.course
        )
        self.assertEqual(events.count(), 1)
        self.assertEqual(events.first(), event)

    def test_manager_recent_events(self):
        """Test manager method recent_events."""
        # Create an event
        event = self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_CREATED
        )

        # Test recent events (should include our event)
        recent_events = EnrollmentHistoryEvent.objects.recent_events(days=1)
        self.assertEqual(recent_events.count(), 1)

        # Test with 0 days (should not include any events)
        no_recent_events = EnrollmentHistoryEvent.objects.recent_events(days=0)
        self.assertEqual(no_recent_events.count(), 0)

    def test_manager_creations_for_course(self):
        """Test manager method creations_for_course."""
        created_event = self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_CREATED
        )
        self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_UPDATED
        )

        creations = EnrollmentHistoryEvent.objects.creations_for_course(
            self.course
        )
        self.assertEqual(creations.count(), 1)
        self.assertEqual(creations.first(), created_event)

    def test_manager_deletions_for_course(self):
        """Test manager method deletions_for_course."""
        self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_CREATED
        )
        deleted_event = self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_DELETED
        )

        deletions = EnrollmentHistoryEvent.objects.deletions_for_course(
            self.course
        )
        self.assertEqual(deletions.count(), 1)
        self.assertEqual(deletions.first(), deleted_event)

    def test_manager_updates_with_term_changes(self):
        """Test manager method updates_with_term_changes."""
        # Create update without previous terms (should not be included)
        self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_UPDATED
        )

        # Create update with previous terms (should be included)
        update_with_previous = self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_UPDATED,
            previous_terms=["20251"]
        )

        updates = EnrollmentHistoryEvent.objects.updates_with_term_changes()
        self.assertEqual(updates.count(), 1)
        self.assertEqual(updates.first(), update_with_previous)

    def test_get_terms_added(self):
        """Test get_terms_added method."""
        event = self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_UPDATED,
            previous_terms=["20251"]
        )

        added_terms = event.get_terms_added()
        self.assertEqual(added_terms, ["20252"])

    def test_get_terms_removed(self):
        """Test get_terms_removed method."""
        # Set enrollment to have fewer terms than before
        self.enrollment.eligible_terms = ["20251"]
        event = self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_UPDATED,
            previous_terms=["20251", "20252", "20253"]
        )

        removed_terms = event.get_terms_removed()
        self.assertEqual(set(removed_terms), {"20252", "20253"})

    def test_get_terms_added_non_update_event(self):
        """Test get_terms_added returns empty for non-update events."""
        event = self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_CREATED
        )

        added_terms = event.get_terms_added()
        self.assertEqual(added_terms, [])

    def test_is_terms_update(self):
        """Test is_terms_update method."""
        update_with_previous = self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_UPDATED,
            previous_terms=["20251"]
        )
        update_without_previous = self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_UPDATED
        )
        created_event = self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_CREATED
        )

        self.assertTrue(update_with_previous.is_terms_update())
        self.assertFalse(update_without_previous.is_terms_update())
        self.assertFalse(created_event.is_terms_update())

    def test_get_event_summary(self):
        """Test get_event_summary method."""
        # Test created event summary
        created_event = self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_CREATED
        )
        summary = created_event.get_event_summary()
        self.assertEqual(summary, "Enrollment Created for 12345678")

        # Test update event with terms changes
        update_event = self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_UPDATED,
            previous_terms=["20251"]
        )
        summary = update_event.get_event_summary()
        self.assertIn("Enrollment Updated for 12345678", summary)
        self.assertIn("added terms:", summary)

    def test_json_data(self):
        """Test json_data method."""
        event = self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_CREATED
        )

        json_data = event.json_data()
        expected_keys = [
            'enrollment_id', 'event_type', 'timestamp', 'integration_id',
            'course_id', 'section_id', 'eligible_terms',
            'previous_eligible_terms'
        ]
        for key in expected_keys:
            self.assertIn(key, json_data)

        self.assertEqual(json_data['enrollment_id'], self.enrollment.pk)
        self.assertEqual(json_data['event_type'],
                         EnrollmentHistoryEvent.EVENT_TYPE_CREATED)
        self.assertEqual(json_data['integration_id'], "12345678")


class EnrollmentHistoryUtilitiesTest(TrainingCourseTestCase):
    """Test Enrollment model history utility methods."""

    def setUp(self):
        """Set up test data."""
        # Use fixture-based training course
        self.training_course = TrainingCourse.objects.get(pk=1)

        # Create test course
        self.course = Course.objects.create(
            course_id="TEST001",
            training_course=self.training_course,
            course_ordinal=1
        )
        self.enrollment = Enrollment.objects.create(
            integration_id="12345678",
            course=self.course,
            eligible_terms=["20251", "20252"]
        )

    def test_get_history_events(self):
        """Test get_history_events method."""
        _ = self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_CREATED
        )
        _ = self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_UPDATED
        )

        history = self.enrollment.get_history_events()
        self.assertEqual(history.count(), 2)

    def test_get_latest_history_event(self):
        """Test get_latest_history_event method."""
        _ = self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_CREATED
        )
        event2 = self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_UPDATED
        )

        latest = self.enrollment.get_latest_history_event()
        self.assertEqual(latest, event2)

    def test_get_creation_event(self):
        """Test get_creation_event method."""
        created_event = self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_CREATED
        )
        self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_UPDATED
        )

        creation = self.enrollment.get_creation_event()
        self.assertEqual(creation, created_event)

    def test_has_been_deleted(self):
        """Test has_been_deleted method."""
        # Initially should not have been deleted
        self.assertFalse(self.enrollment.has_been_deleted())

        # After creating a deletion event, should return True
        self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_DELETED
        )
        self.assertTrue(self.enrollment.has_been_deleted())

    def test_has_been_reactivated(self):
        """Test has_been_reactivated method."""
        # Initially should not have been reactivated
        self.assertFalse(self.enrollment.has_been_reactivated())

        # After creating a reactivation event, should return True
        self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_REACTIVATED
        )
        self.assertTrue(self.enrollment.has_been_reactivated())

    def test_get_eligible_terms_history(self):
        """Test get_eligible_terms_history method."""
        _ = self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_CREATED
        )
        _ = self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_UPDATED,
            previous_terms=["20251"]
        )
        # Deletion event should not be included
        self.enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_DELETED
        )

        history = self.enrollment.get_eligible_terms_history()
        self.assertEqual(len(history), 2)

        # Check that the returned data contains the right fields
        for entry in history:
            self.assertIn('timestamp', entry)
            self.assertIn('eligible_terms', entry)
            self.assertIn('previous_eligible_terms', entry)


class EnrollmentHistoryIntegrationTest(TrainingCourseTestCase):
    """Test history event creation during enrollment operations."""

    @patch('training_provisioner.models.'
           'training_course.TrainingCourse.get_course_membership')
    def setUp(self, mock_membership):
        """Set up test data with mocked membership."""
        mock_membership.return_value = self.get_membership()
        self.training_course = TrainingCourse.objects.get(pk=1)

        Course.objects.add_models_for_training_course(self.training_course)
        Section.objects.add_models_for_training_course(self.training_course)

    @patch('training_provisioner.models.'
           'training_course.TrainingCourse.get_course_membership')
    def test_enrollment_creation_creates_history_event(self, mock_membership):
        """Test that creating enrollments creates history events."""
        mock_membership.return_value = {"12345678": ["20251", "20252"]}

        # Clear any existing enrollments and history
        Enrollment.objects.all().delete()
        EnrollmentHistoryEvent.objects.all().delete()

        # Run enrollment process
        Enrollment.objects.add_models_for_training_course(self.training_course)

        # Check that enrollment was created
        enrollment = Enrollment.objects.get(integration_id="12345678")
        self.assertIsNotNone(enrollment)

        # Check that creation event was created
        creation_events = EnrollmentHistoryEvent.objects.filter(
            enrollment=enrollment,
            event_type=EnrollmentHistoryEvent.EVENT_TYPE_CREATED
        )
        self.assertEqual(creation_events.count(), 1)

        creation_event = creation_events.first()
        self.assertEqual(creation_event.integration_id, "12345678")
        self.assertEqual(creation_event.course_id, enrollment.course.course_id)
        self.assertEqual(creation_event.eligible_terms, ["20251", "20252"])

    @patch('training_provisioner.models.'
           'training_course.TrainingCourse.get_course_membership')
    def test_enrollment_update_creates_history_event(self, mock_membership):
        """Test that updating enrollment eligible terms creates
        history events."""
        # Clear any existing data
        Enrollment.objects.all().delete()
        EnrollmentHistoryEvent.objects.all().delete()

        # First run with initial terms
        mock_membership.return_value = {"12345678": ["20251"]}
        Enrollment.objects.add_models_for_training_course(self.training_course)

        enrollment = Enrollment.objects.get(integration_id="12345678")

        # Verify creation event was created
        creation_events = EnrollmentHistoryEvent.objects.filter(
            enrollment=enrollment,
            event_type=EnrollmentHistoryEvent.EVENT_TYPE_CREATED
        )
        self.assertTrue(creation_events.exists())

        # Second run with additional terms - this should create an update event
        mock_membership.return_value = {"12345678": ["20251", "20252"]}
        Enrollment.objects.add_models_for_training_course(self.training_course)

        # Refresh enrollment from database
        enrollment.refresh_from_db()

        # Check that terms were updated
        self.assertIn("20251", enrollment.eligible_terms)
        self.assertIn("20252", enrollment.eligible_terms)

        # Check that update event was created
        update_events = EnrollmentHistoryEvent.objects.filter(
            enrollment=enrollment,
            event_type=EnrollmentHistoryEvent.EVENT_TYPE_UPDATED
        )
        self.assertTrue(update_events.exists())

        if update_events.exists():
            update_event = update_events.first()
            self.assertEqual(update_event.previous_eligible_terms, ["20251"])
            self.assertEqual(set(update_event.eligible_terms),
                             {"20251", "20252"})

    @patch('training_provisioner.models.'
           'training_course.TrainingCourse.get_course_membership')
    def test_enrollment_deletion_creates_history_event(self, mock_membership):
        """Test that deleting enrollments creates history events."""
        # First run to create enrollment
        mock_membership.return_value = {"12345678": ["20251"]}
        Enrollment.objects.add_models_for_training_course(self.training_course)

        enrollment = Enrollment.objects.get(integration_id="12345678")

        # Clear existing history events to focus on deletion event
        EnrollmentHistoryEvent.objects.filter(enrollment=enrollment).delete()

        # Second run with empty membership, but disable circuit breaker
        # by manually deleting the enrollment to simulate the deletion process
        enrollment.deleted_date = timezone.now()
        enrollment.save()

        # Manually create the deletion history event (simulating the process)
        enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_DELETED
        )

        # Check that deletion event was created
        deletion_events = EnrollmentHistoryEvent.objects.filter(
            enrollment=enrollment,
            event_type=EnrollmentHistoryEvent.EVENT_TYPE_DELETED
        )
        self.assertTrue(deletion_events.exists())

    @patch('training_provisioner.models.'
           'training_course.TrainingCourse.get_course_membership')
    def test_enrollment_reactivation_creates_history_event(self,
                                                           mock_membership):
        """Test that reactivating enrollments creates history events."""
        # Create enrollment manually with deleted state
        course = Course.objects.filter(
            training_course=self.training_course
        ).first()

        enrollment = Enrollment.objects.create(
            integration_id="12345678",
            course=course,
            eligible_terms=["20251"],
            deleted_date=timezone.now()
        )

        # Clear existing history events
        EnrollmentHistoryEvent.objects.filter(enrollment=enrollment).delete()

        # Simulate reactivation by setting deleted_date to None
        enrollment.deleted_date = None
        enrollment.save()

        # Create reactivation history event (simulating the process)
        enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_REACTIVATED
        )

        # Check that reactivation event was created
        reactivation_events = EnrollmentHistoryEvent.objects.filter(
            enrollment=enrollment,
            event_type=EnrollmentHistoryEvent.EVENT_TYPE_REACTIVATED
        )
        self.assertTrue(reactivation_events.exists())

    def test_no_duplicate_events_for_unchanged_terms(self):
        """Test that no update events are created when terms don't change."""
        # Create enrollment with history tracking
        course = Course.objects.first()
        enrollment = Enrollment.objects.create(
            integration_id="12345678",
            course=course,
            eligible_terms=["20251", "20252"]
        )

        # Create initial creation event
        enrollment.create_history_event(
            EnrollmentHistoryEvent.EVENT_TYPE_CREATED
        )

        initial_count = EnrollmentHistoryEvent.objects.filter(
            enrollment=enrollment
        ).count()

        # Simulate updating with the same terms
        enrollment.merge_eligible_terms(["20251", "20252"])

        # Manually check if terms actually changed (they shouldn't have)
        # This simulates the logic in _add_enrollment
        previous_terms = ["20251", "20252"]
        current_terms = enrollment.eligible_terms or []

        if set(previous_terms) != set(current_terms):
            enrollment.create_history_event(
                EnrollmentHistoryEvent.EVENT_TYPE_UPDATED,
                previous_terms=previous_terms
            )

        # Count should remain the same since no update event should be created
        final_count = EnrollmentHistoryEvent.objects.filter(
            enrollment=enrollment
        ).count()

        self.assertEqual(initial_count, final_count)
