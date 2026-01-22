# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from training_provisioner.views.api import StudentTrainingAPI
from training_provisioner.models.enrollment import Enrollment


class Enrollments(StudentTrainingAPI):
    def get(self, request, *args, **kwargs):
        try:
            integration_id = kwargs.get('integration_id')
            enrollments = Enrollment.objects.filter(
                integration_id=integration_id)
            return self.json_response([e.json_data() for e in enrollments])
        except Exception as ex:
            return self.error_response(str(ex))
