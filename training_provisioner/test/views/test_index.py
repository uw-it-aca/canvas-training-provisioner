# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from django.test import TestCase, RequestFactory, override_settings
from django.urls import reverse
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.models import User
from training_provisioner.views.index import IndexView
import mock


@override_settings(
    RESTCLIENTS_CANVAS_ACCOUNT_ID=123,
    STUDENTTRAINING_ADMIN_GROUP='u_acadev_unittest')
class IndexViewTest(TestCase):
    def setUp(self):
        self.request = RequestFactory().get(
            reverse('index'), HTTP_HOST='example.uw.edu')
        get_response = mock.MagicMock()
        middleware = SessionMiddleware(get_response)
        response = middleware(self.request)
        self.request.user = User.objects.create_user(username='jstaff')

    def test_home_view(self):
        self.request.session['samlUserdata'] = {
            'uwnetid': ['jstaff'], 'isMemberOf': ['uw_member']}

        response = IndexView.as_view()(self.request)

        self.assertEqual(response.status_code, 200)

    def test_home_view_admin(self):
        self.request.session['samlUserdata'] = {
            'uwnetid': ['jstaff'], 'isMemberOf': ['u_acadev_unittest']}

        response = IndexView.as_view()(self.request)

        self.assertEqual(response.status_code, 302)
