# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.http import HttpResponse, JsonResponse
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.exceptions import APIException


class StudentTrainingAPI(APIView):
    """
        API base class definint authentication and permission
    """

    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def json_response(self, data, status=200):
        return JsonResponse(data, status=status, safe=False)

    def error_response(self, message, status=400):
        return JsonResponse({'error': message}, status=status)
