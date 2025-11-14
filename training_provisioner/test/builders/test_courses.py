# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from training_provisioner.test import TrainingCourseTestCase
from training_provisioner.models.training_course import TrainingCourse
from training_provisioner.builders.courses import CourseBuilder
from training_provisioner.models.course import Course
from django.core.files.storage import default_storage
from django.test import override_settings
import os


class CourseBuilderTest(TrainingCourseTestCase):
    def test_course_builder(self):
        builder = CourseBuilder()

        self.assertEqual(builder.build(), None)

    @override_settings(
        TRAINING_IMPORT_CSV_DEBUG=False,
        STORAGES={
            "default": {
                "BACKEND": "django.core.files.storage.memory.InMemoryStorage",
            },
        }
    )
    def test_course_builder_with_data(self):
        for training_course in TrainingCourse.objects.active_courses():
            Course.objects.add_models_for_training_course(training_course)

        courses = Course.objects.all()
        builder = CourseBuilder(courses)
        csv_path = builder.build()

        self.assertIsNotNone(csv_path)

        filename = os.path.join(csv_path, 'courses.csv')
        with default_storage.open(filename, mode='r') as f:
            csv_data = f.readlines()

        self.assertEqual(len(csv_data) - 1, courses.count())
