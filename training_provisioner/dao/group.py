# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.conf import settings
from uw_saml.utils import is_member_of_group


def is_admin_user(request):
    """
    This check is always a SAML-asserted group membership.
    """
    return is_member_of_group(request, settings.STUDENTTRAINING_ADMIN_GROUP)
