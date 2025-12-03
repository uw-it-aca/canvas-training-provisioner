# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from django.contrib import admin
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from uw_saml.decorators import group_required
from django.http import HttpResponseRedirect
from django.urls import reverse
from training_provisioner.models import Import
from training_provisioner.models.training_course import TrainingCourse
from training_provisioner.dao.group import is_admin_user


class SAMLAdminSite(admin.AdminSite):
    site_header = 'Student Training Provisioner Admin'

    def __init__(self, *args, **kwargs):
        super(SAMLAdminSite, self).__init__(*args, **kwargs)
        self._registry.update(admin.site._registry)

    def has_permission(self, request):
        return is_admin_user(request)

    def login(self, request, extra_context=None):
        if self.has_permission(request):
            index_path = reverse('admin:index', current_app=self.name)
            return HttpResponseRedirect(index_path)
        else:
            return HttpResponseRedirect('/not-authorized/')


class AbstractSAMLAdminModel():
    def has_add_permission(self, request):
        return is_admin_user(request)

    def has_change_permission(self, request, obj=None):
        return is_admin_user(request)

    def has_delete_permission(self, request, obj=None):
        return is_admin_user(request)

    def has_module_permission(self, request):
        return is_admin_user(request)


class AbstractSAMLReadOnlyAdminModel():
    def has_view_permission(self, request, obj=None):
        return is_admin_user(request)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return is_admin_user(request)

    def has_module_permission(self, request):
        return is_admin_user(request)


class SAMLAdminModel(AbstractSAMLAdminModel, admin.ModelAdmin):
    pass


class SAMLReadOnlyAdminModel(AbstractSAMLReadOnlyAdminModel, admin.ModelAdmin):
    pass


class SAMLAdminTrainingCourseModel(SAMLAdminModel):
    readonly_fields = ['creation_date', 'deleted_date']

    def get_readonly_fields(self, request, obj=None):
        dependent_fields = []

        if obj and obj.is_provisioned:  # editing an existing object
            dependent_fields = ['course_count', 'membership_type']

        return self.readonly_fields + dependent_fields


admin_site = SAMLAdminSite(name='SAMLAdmin')
admin_site.register(TrainingCourse, SAMLAdminTrainingCourseModel)
admin_site.register(Import, SAMLReadOnlyAdminModel)
