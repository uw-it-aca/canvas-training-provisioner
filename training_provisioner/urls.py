# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.urls import re_path
from training_provisioner.views.api.enrollments import Enrollments


urlpatterns = [
    re_path('api/v1/student/(?P<integration_id>[0-9]{7})/enrollments/?',
            Enrollments.as_view(),
            name='student_enrollments'),
]
