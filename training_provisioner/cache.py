# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from memcached_clients import RestclientPymemcacheClient
import re

ONE_MINUTE = 60
ONE_HOUR = 60 * 60
ONE_DAY = 60 * 60 * 24
ONE_WEEK = 60 * 60 * 24 * 7
ONE_MONTH = 60 * 60 * 24 * 30


class RestClientsCache(RestclientPymemcacheClient):
    def get_cache_expiration_time(self, service, url, status=200):
        if 'canvas' == service:
            if re.match(r'^/api/v\d/courses/', url):
                return ONE_HOUR * 10
