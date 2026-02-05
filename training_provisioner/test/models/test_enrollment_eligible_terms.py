# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.test import TestCase
from training_provisioner.models.enrollment import Enrollment
from training_provisioner.models.course import Course
from training_provisioner.models.training_course import TrainingCourse
from training_provisioner.test import TrainingCourseTestCase


class EnrollmentEligibleTermsTest(TrainingCourseTestCase):
    """Test the eligible_terms functionality in Enrollment model."""

    def setUp(self):
        super().setUp()
        self.training_course = TrainingCourse.objects.get(pk=1)

        # Create a course for testing
        Course.objects.add_models_for_training_course(self.training_course)
        self.course = Course.objects.filter(
            training_course=self.training_course).first()

    def test_merge_eligible_terms_empty_existing(self):
        """Test merging terms when enrollment has no existing terms."""
        enrollment = Enrollment.objects.create(
            course=self.course,
            integration_id="1234567",
            eligible_terms=[]
        )

        new_terms = ["20254R", "20261A"]
        enrollment.merge_eligible_terms(new_terms)

        self.assertEqual(set(enrollment.eligible_terms), {"20254R", "20261A"})

    def test_merge_eligible_terms_existing_terms(self):
        """Test merging terms when enrollment has existing terms."""
        enrollment = Enrollment.objects.create(
            course=self.course,
            integration_id="1234567",
            eligible_terms=["20254R", "20262A"]
        )

        new_terms = ["20261A", "20262R"]  # 20262A is duplicate
        enrollment.merge_eligible_terms(new_terms)

        # Should have unique terms from both sets
        expected_terms = {"20254R", "20261A", "20262A", "20262R"}
        self.assertEqual(set(enrollment.eligible_terms), expected_terms)

    def test_merge_eligible_terms_duplicates(self):
        """Test merging terms with duplicates."""
        enrollment = Enrollment.objects.create(
            course=self.course,
            integration_id="1234567",
            eligible_terms=["20254R", "20261A"]
        )

        new_terms = ["20254R", "20261A", "20262R"]  # First two are duplicates
        enrollment.merge_eligible_terms(new_terms)

        # Should deduplicate
        expected_terms = {"20254R", "20261A", "20262R"}
        self.assertEqual(set(enrollment.eligible_terms), expected_terms)

    def test_merge_eligible_terms_none_input(self):
        """Test merging terms with None input."""
        enrollment = Enrollment.objects.create(
            course=self.course,
            integration_id="1234567",
            eligible_terms=["20254R"]
        )

        enrollment.merge_eligible_terms(None)

        # Should remain unchanged
        self.assertEqual(enrollment.eligible_terms, ["20254R"])

    def test_merge_eligible_terms_empty_input(self):
        """Test merging terms with empty list input."""
        enrollment = Enrollment.objects.create(
            course=self.course,
            integration_id="1234567",
            eligible_terms=["20254R"]
        )

        enrollment.merge_eligible_terms([])

        # Should remain unchanged
        self.assertEqual(enrollment.eligible_terms, ["20254R"])

    def test_json_data_includes_eligible_terms(self):
        """Test that json_data includes eligible_terms."""
        enrollment = Enrollment.objects.create(
            course=self.course,
            integration_id="1234567",
            eligible_terms=["20254R", "20261A"]
        )

        json_data = enrollment.json_data()

        self.assertIn('eligible_terms', json_data)
        self.assertEqual(set(json_data['eligible_terms']),
                         {"20254R", "20261A"})
