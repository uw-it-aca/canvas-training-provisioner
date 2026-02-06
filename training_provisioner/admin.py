# Copyright 2026 UW-IT, University of Washington
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
from training_provisioner.models.enrollment import (
    Enrollment, EnrollmentHistoryEvent)
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

        if obj and obj.pk:  # editing an existing object
            dependent_fields = [
                'course_count', 'membership_type', 'course_type',
                'term_id', 'blueprint_course_id']

        return self.readonly_fields + dependent_fields


class SAMLAdminEnrollmentModel(SAMLReadOnlyAdminModel):
    """Read-only admin interface for Enrollment model."""
    list_display = ['integration_id', 'course', 'section',
                    'eligible_terms_display', 'created_date', 'deleted_date']
    list_filter = ['created_date', 'deleted_date', 'course__training_course']
    search_fields = ['integration_id', 'course__course_id']
    readonly_fields = ['integration_id', 'course', 'section',
                       'eligible_terms', 'created_date', 'deleted_date',
                       'priority']

    def eligible_terms_display(self, obj):
        """Display eligible terms as comma-separated string."""
        if obj.eligible_terms:
            return ', '.join(obj.eligible_terms)
        return 'None'
    eligible_terms_display.short_description = 'Eligible Terms'

    def has_view_permission(self, request, obj=None):
        return is_admin_user(request)


class SAMLAdminEnrollmentHistoryEventModel(SAMLReadOnlyAdminModel):
    """Read-only admin interface for EnrollmentHistoryEvent model."""
    list_display = ['timestamp', 'enrollment', 'event_type',
                    'integration_id', 'course_id', 'eligible_terms_display']
    list_filter = ['event_type', 'timestamp']
    search_fields = ['integration_id', 'course_id']
    readonly_fields = ['enrollment', 'event_type', 'integration_id',
                       'course_id', 'section_id', 'eligible_terms',
                       'previous_eligible_terms', 'timestamp']
    ordering = ['-timestamp']

    def eligible_terms_display(self, obj):
        """Display eligible terms as comma-separated string."""
        if obj.eligible_terms:
            return ', '.join(obj.eligible_terms)
        return 'None'
    eligible_terms_display.short_description = 'Eligible Terms'

    def has_view_permission(self, request, obj=None):
        return is_admin_user(request)


admin_site = SAMLAdminSite(name='SAMLAdmin')
admin_site.register(TrainingCourse, SAMLAdminTrainingCourseModel)
admin_site.register(Import, SAMLReadOnlyAdminModel)
admin_site.register(Enrollment, SAMLAdminEnrollmentModel)
admin_site.register(EnrollmentHistoryEvent,
                    SAMLAdminEnrollmentHistoryEventModel)
