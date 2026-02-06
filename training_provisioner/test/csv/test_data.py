# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from training_provisioner.test import TrainingCourseTestCase
from training_provisioner.builders.courses import CourseBuilder
from training_provisioner.csv.format import *
from training_provisioner.csv.data import Collector
import mock


class InvalidFormat(CSVFormat):
    pass


class CSVDataTest(TrainingCourseTestCase):
    def test_invalid_format(self):
        csv = Collector()
        self.assertRaises(TypeError, csv.add, InvalidFormat)
        self.assertEqual(csv.has_data(), False)

    @mock.patch('training_provisioner.csv.data.default_storage.open')
    def test_write_files(self, mock_open):
        # Test empty
        csv = Collector()
        self.assertEqual(csv.has_data(), False)
        self.assertEqual(csv.write_files(), None)

        # Test with data
        csv = Collector()
        csv.enrollments.append(1)
        self.assertEqual(csv.has_data(), True)

        with self.settings(TRAINING_IMPORT_CSV_DEBUG=False):
            path = csv.write_files()
            mock_open.assert_called_with(path + '/enrollments.csv', mode='w')
            self.assertEqual(csv.has_data(), False)
