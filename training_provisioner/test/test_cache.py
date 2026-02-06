# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.test import TestCase
from unittest.mock import patch, MagicMock
import sys

# Mock the missing memcached_clients module
if 'memcached_clients' not in sys.modules:
    memcached_mock = MagicMock()
    memcached_mock.RestclientPymemcacheClient = MagicMock
    sys.modules['memcached_clients'] = memcached_mock

# Try to import the cache module
try:
    from training_provisioner.cache import (
        RestClientsCache, ONE_MINUTE, ONE_HOUR, ONE_DAY, ONE_WEEK, ONE_MONTH
    )
    CACHE_AVAILABLE = True
except ImportError as e:
    CACHE_AVAILABLE = False
    print(f"Cache import failed: {e}")


class RestClientsCacheTest(TestCase):
    def setUp(self):
        """Set up test cache instance."""
        self.cache = RestClientsCache()

    def test_time_constants(self):
        """Test that time constants are correctly defined."""
        self.assertEqual(ONE_MINUTE, 60)
        self.assertEqual(ONE_HOUR, 60 * 60)
        self.assertEqual(ONE_DAY, 60 * 60 * 24)
        self.assertEqual(ONE_WEEK, 60 * 60 * 24 * 7)
        self.assertEqual(ONE_MONTH, 60 * 60 * 24 * 30)

    def test_canvas_courses_api_cache_expiration(self):
        """Test cache expiration for Canvas courses API endpoints."""
        # Test various Canvas courses API URLs
        test_cases = [
            '/api/v1/courses/123',
            '/api/v2/courses/456/enrollments',
            '/api/v1/courses/789/sections',
            '/api/v3/courses/101/assignments',
        ]

        for url in test_cases:
            with self.subTest(url=url):
                expiration = self.cache.get_cache_expiration_time(
                    'canvas', url)
                self.assertEqual(expiration, ONE_HOUR * 10)

    def test_canvas_courses_api_with_status_codes(self):
        """Test cache expiration for Canvas courses API with different status
          codes.
        """
        url = '/api/v1/courses/123'

        # Test with various status codes
        status_codes = [200, 201, 404, 500]
        for status in status_codes:
            with self.subTest(status=status):
                expiration = self.cache.get_cache_expiration_time(
                    'canvas', url, status)
                self.assertEqual(expiration, ONE_HOUR * 10)

    def test_canvas_non_courses_api_urls(self):
        """Test that non-courses Canvas API URLs return None
        (default behavior).
        """
        test_cases = [
            '/api/v1/accounts/123',
            '/api/v1/users/456',
            '/api/v2/enrollments',
            '/api/v1/sections/789',
            '/some/other/endpoint',
            '',
        ]

        for url in test_cases:
            with self.subTest(url=url):
                expiration = self.cache.get_cache_expiration_time(
                    'canvas', url)
                self.assertIsNone(expiration)

    def test_non_canvas_services(self):
        """Test that non-canvas services return None (default behavior)."""
        test_services = [
            'sws',
            'pws',
            'gws',
            'uwnetid',
            'some_other_service',
            '',
        ]

        url = '/api/v1/courses/123'
        for service in test_services:
            with self.subTest(service=service):
                expiration = self.cache.get_cache_expiration_time(service, url)
                self.assertIsNone(expiration)

    def test_edge_cases(self):
        """Test edge cases and malformed inputs."""
        # Test with None values - should handle gracefully
        expiration = self.cache.get_cache_expiration_time(
            None, '/api/v1/courses/123')
        self.assertIsNone(expiration)

        # Test with None URL - this will cause a TypeError in the current
        # implementation which is the expected behavior since re.match expects
        # a string
        with self.assertRaises(TypeError):
            self.cache.get_cache_expiration_time('canvas', None)

        # Test with empty strings
        expiration = self.cache.get_cache_expiration_time(
            '', '/api/v1/courses/123')
        self.assertIsNone(expiration)

        expiration = self.cache.get_cache_expiration_time('canvas', '')
        self.assertIsNone(expiration)

    def test_courses_api_regex_patterns(self):
        """Test the regex pattern matching for courses API endpoints."""
        # Test URLs that should match (single digit version numbers)
        matching_urls = [
            '/api/v1/courses/',
            '/api/v1/courses/123',
            '/api/v2/courses/456/enrollments',
            '/api/v9/courses/test',
        ]

        for url in matching_urls:
            with self.subTest(url=url, should_match=True):
                expiration = self.cache.get_cache_expiration_time(
                    'canvas', url)
                self.assertEqual(expiration, ONE_HOUR * 10)

        # Test URLs that should NOT match
        non_matching_urls = [
            '/api/courses/123',  # missing version
            'api/v1/courses/123',  # missing leading slash
            '/api/v1/course/123',  # singular "course"
            '/api/v/courses/123',  # invalid version format
            '/api/v1/courses',  # missing trailing slash
            '/api/v1/something/courses/123',  # extra path segment
            '/api/v10/courses/test',  # multi-digit (doesn't match \d pattern)
            '/api/v999/courses/some-course-id',  # multi-digit version
        ]

        for url in non_matching_urls:
            with self.subTest(url=url, should_match=False):
                expiration = self.cache.get_cache_expiration_time(
                    'canvas', url)
                self.assertIsNone(expiration)

    def test_inheritance_from_parent_class(self):
        """Test that RestClientsCache properly inherits from
           RestclientPymemcacheClient.
        """
        from memcached_clients import RestclientPymemcacheClient
        self.assertTrue(issubclass(RestClientsCache,
                                   RestclientPymemcacheClient))

    def test_method_signature(self):
        """Test that the method signature is correct."""
        import inspect
        signature = inspect.signature(self.cache.get_cache_expiration_time)

        # Check parameter names and defaults
        params = signature.parameters
        self.assertIn('service', params)
        self.assertIn('url', params)
        self.assertIn('status', params)
        self.assertEqual(params['status'].default, 200)


# Test that can run even without cache dependencies
class CacheConstantsTest(TestCase):
    """Test cache constants that should always be available."""

    def test_time_constants_defined(self):
        """Test that time constants are properly defined in the module."""
        if CACHE_AVAILABLE:
            # If cache is available, test the actual constants
            self.assertEqual(ONE_MINUTE, 60)
            self.assertEqual(ONE_HOUR, 60 * 60)
            self.assertEqual(ONE_DAY, 60 * 60 * 24)
            self.assertEqual(ONE_WEEK, 60 * 60 * 24 * 7)
            self.assertEqual(ONE_MONTH, 60 * 60 * 24 * 30)
        else:
            # If cache isn't available, just verify the module can be analyzed
            import ast
            import os

            cache_file = os.path.join(os.path.dirname(__file__), '..',
                                      'cache.py')
            with open(cache_file, 'r') as f:
                content = f.read()

            # Parse the AST to verify constants are defined
            tree = ast.parse(content)
            assignments = [node for node in ast.walk(tree) if isinstance(
                node, ast.Assign)]
            constant_names = []
            for assign in assignments:
                for target in assign.targets:
                    if isinstance(target, ast.Name):
                        constant_names.append(target.id)

            expected_constants = ['ONE_MINUTE', 'ONE_HOUR', 'ONE_DAY',
                                  'ONE_WEEK', 'ONE_MONTH']
            for constant in expected_constants:
                self.assertIn(constant, constant_names, f"Constant {constant} "
                              "should be defined")

    def test_cache_module_structure(self):
        """Test that the cache module has the expected structure."""
        import ast
        import os

        cache_file = os.path.join(os.path.dirname(__file__), '..', 'cache.py')
        with open(cache_file, 'r') as f:
            content = f.read()

        # Parse AST to verify module structure
        tree = ast.parse(content)

        # Check for class definition
        classes = [node for node in ast.walk(tree) if isinstance(
            node, ast.ClassDef)]
        class_names = [cls.name for cls in classes]
        self.assertIn('RestClientsCache', class_names,
                      "RestClientsCache class should be defined")

        # Check for method definition
        methods = []
        for cls in classes:
            if cls.name == 'RestClientsCache':
                methods = [node.name for node in cls.body if isinstance(
                    node, ast.FunctionDef)]

        self.assertIn('get_cache_expiration_time', methods,
                      "get_cache_expiration_time method should be defined")
