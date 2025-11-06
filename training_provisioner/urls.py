# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.urls import re_path
from training_provisioner.views.api.enrollments import Enrollments
from training_provisioner.views.api.imports import ImportView, ImportListView


urlpatterns = [
    re_path('api/v1/student/(?P<integration_id>[0-9]{7})/enrollments/?',
            Enrollments.as_view(), name='student_enrollments'),
    re_path(r'api/v1/import/(?P<import_id>[0-9]+)?$',
            ImportView.as_view(), name='import_view'),
    re_path(r'api/v1/imports/?$',
            ImportListView.as_view(), name='import_list'),
]
