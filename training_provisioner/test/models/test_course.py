# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.test import TestCase
from training_provisioner.models import CourseBlueprint
import mock


class CourseBlueprintModelTest(TestCase):
    @mock.patch.object(
        'training_provisioner.dao.membership.get_title_vi_membership')
    def test_membership(self):
        mock_get_data.return_value = ['12345678']

