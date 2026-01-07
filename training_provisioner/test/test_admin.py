# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from django.test import TestCase, RequestFactory, override_settings
from django.urls import reverse
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.models import User
from training_provisioner.admin import admin_site
import mock


@override_settings(
    RESTCLIENTS_CANVAS_ACCOUNT_ID=123,
    STUDENTTRAINING_ADMIN_GROUP='u_acadev_unittest')
class AdminSiteLoginTest(TestCase):
    def setUp(self):
        self.url = reverse('admin:login')
        self.request = RequestFactory().get(
            self.url, HTTP_HOST='example.uw.edu')
        get_response = mock.MagicMock()
        middleware = SessionMiddleware(get_response)
        response = middleware(self.request)
        self.request.user = User.objects.create_user(username='jstaff')
        self.saml_user_data = {'uwnetid': ['jstaff']}
        self.request.session['samlUserdata'] = self.saml_user_data

    def test_admin_login(self):
        self.saml_user_data['isMemberOf'] = ['u_acadev_unittest']
        response = admin_site.login(self.request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('admin:index'))

    def test_unauthorized_admin_login(self):
        self.saml_user_data['isMemberOf'] = ['uw_member']
        response = admin_site.login(self.request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/not-authorized/')


@override_settings(
    RESTCLIENTS_CANVAS_ACCOUNT_ID=123,
    STUDENTTRAINING_ADMIN_GROUP='u_acadev_unittest')
class AdminSiteIndexTest(TestCase):
    def setUp(self):
        self.url = reverse('admin:index')
        self.request = RequestFactory().get(
            self.url, HTTP_HOST='example.uw.edu')
        get_response = mock.MagicMock()
        middleware = SessionMiddleware(get_response)
        response = middleware(self.request)
        self.request.user = User.objects.create_user(username='jstaff')
        self.saml_user_data = {'uwnetid': ['jstaff']}
        self.request.session['samlUserdata'] = self.saml_user_data

    def test_admin_view(self):
        self.saml_user_data['isMemberOf'] = ['u_acadev_unittest']
        response = admin_site.index(self.request)

        self.assertEqual(response.status_code, 200)

    def test_unauthorized_admin_view(self):
        self.saml_user_data['isMemberOf'] = ['uw_member']
        response = admin_site.index(self.request)

        self.assertContains(
            response,
            (b'You don\xe2\x80\x99t have permission '
             b'to view or edit anything').decode('utf-8'),
            status_code=200)
