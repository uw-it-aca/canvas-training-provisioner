# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.urls import re_path
from django.views.generic.base import TemplateView
from training_provisioner.admin import admin_site
from training_provisioner.views.index import IndexView
from training_provisioner.views.api.enrollments import Enrollments
from training_provisioner.views.api.imports import ImportView, ImportListView


urlpatterns = [
    re_path(r'^$', IndexView.as_view(), name="index"),
    re_path(r"^admin/?", admin_site.urls),
    re_path(
        r"^not-authorized/?$",
        TemplateView.as_view(template_name="unauthorized-user.html"),
        name="unauthorized_user",
    ),
    re_path('api/v1/student/(?P<integration_id>[0-9]{7})/enrollments/?',
            Enrollments.as_view(), name='student_enrollments'),
    re_path(r'api/v1/import/(?P<import_id>[0-9]+)?$',
            ImportView.as_view(), name='import_view'),
    re_path(r'api/v1/imports/?$',
            ImportListView.as_view(), name='import_list'),
]
