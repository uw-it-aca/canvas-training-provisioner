# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from unittest.mock import patch, MagicMock, mock_open
import pandas as pd
import json
from django.test import TestCase, override_settings
import sqlalchemy.exc
from training_provisioner.dao.edw import EDWConnection, execute_edw_query
from training_provisioner.exceptions import DataAccessException


class EDWConnectionTest(TestCase):

    def setUp(self):
        self.mock_data = {
            "data": [
                {"id": 1, "name": "Test Student 1"},
                {"id": 2, "name": "Test Student 2"}
            ],
            "columns": ["id", "name"],
            "description": "Test mock data"
        }

    @override_settings(EDW_USE_MOCK_DATA=True)
    def test_init_with_mock_data(self):
        """Test EDWConnection initialization with mock data enabled."""
        edw = EDWConnection()
        self.assertTrue(edw.use_mock_data)
        self.assertIsNone(getattr(edw, 'host', None))
        self.assertIsNone(getattr(edw, 'user', None))
        self.assertIsNone(getattr(edw, 'password', None))

    @override_settings(
        EDW_USE_MOCK_DATA=False,
        EDW_HOST=None,
        EDW_USER=None,
        EDW_PASS=None
    )
    def test_init_missing_settings(self):
        """Test EDWConnection initialization with missing required settings."""
        with self.assertRaises(ValueError) as context:
            EDWConnection()

        self.assertIn("EDW connection parameters", str(context.exception))
        self.assertIn("must be configured", str(context.exception))

    @override_settings(
        EDW_USE_MOCK_DATA=False,
        EDW_HOST='test.host.com',
        EDW_USER='test\\user',
        EDW_PASS='testpass123'
    )
    def test_get_connection_string(self):
        """Test connection string generation."""
        edw = EDWConnection()
        conn_string = edw._get_connection_string()

        # Should properly URL encode the username with backslash
        self.assertIn('mssql+pymssql://', conn_string)
        self.assertIn('test%5Cuser', conn_string)  # URL encoded backslash
        self.assertIn('testpass123', conn_string)
        self.assertIn('@test.host.com', conn_string)

    def test_execute_query_empty_query(self):
        """Test execute_query with empty query."""
        edw = EDWConnection()

        with self.assertRaises(ValueError) as context:
            edw.execute_query("")

        self.assertIn("Query cannot be empty", str(context.exception))

        with self.assertRaises(ValueError) as context:
            edw.execute_query("   ")

        self.assertIn("Query cannot be empty", str(context.exception))

    @override_settings(EDW_USE_MOCK_DATA=True)
    @patch('training_provisioner.dao.edw.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_execute_query_mock_data_success(self, mock_file, mock_exists):
        """Test execute_query with mock data - successful case."""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(self.mock_data)

        edw = EDWConnection()
        result = edw.execute_query("SELECT * FROM test")

        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        self.assertListEqual(list(result.columns), ["id", "name"])
        self.assertEqual(result.iloc[0]['name'], "Test Student 1")

    @override_settings(EDW_USE_MOCK_DATA=True)
    @patch('training_provisioner.dao.edw.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_execute_query_mock_data_no_specific_file(self,
                                                      mock_file,
                                                      mock_exists):
        """
        Test execute_query with mock data - no specific file, uses default.
        """
        def mock_exists_side_effect(path):
            return 'default.json' in path

        mock_exists.side_effect = mock_exists_side_effect
        mock_file.return_value.read.return_value = json.dumps(self.mock_data)

        edw = EDWConnection()
        result = edw.execute_query("SELECT * FROM test")

        self.assertIsInstance(result, pd.DataFrame)
        # Should have called with default.json path
        mock_file.assert_called()

    @override_settings(EDW_USE_MOCK_DATA=True)
    @patch('training_provisioner.dao.edw.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_execute_query_mock_data_file_error(self, mock_file, mock_exists):
        """Test execute_query with mock data - file read error."""
        mock_exists.return_value = True
        mock_file.side_effect = FileNotFoundError("File not found")

        edw = EDWConnection()
        result = edw.execute_query("SELECT * FROM test")

        # Should return empty DataFrame on error
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 0)

    @override_settings(EDW_USE_MOCK_DATA=True)
    @patch('training_provisioner.dao.edw.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_execute_query_mock_data_invalid_json(self,
                                                  mock_file,
                                                  mock_exists):
        """Test execute_query with mock data - invalid JSON."""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = "invalid json {"

        edw = EDWConnection()
        result = edw.execute_query("SELECT * FROM test")

        # Should return empty DataFrame on JSON error
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 0)

    @override_settings(
        EDW_USE_MOCK_DATA=False,
        EDW_HOST='test.host.com',
        EDW_USER='testuser',
        EDW_PASS='testpass'
    )
    @patch('training_provisioner.dao.edw.sqlalchemy.create_engine')
    @patch('training_provisioner.dao.edw.pd.read_sql')
    def test_execute_query_real_success(self,
                                        mock_read_sql,
                                        mock_create_engine):
        """Test execute_query with real database - successful case."""
        # Mock successful database interaction
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = \
            mock_connection
        mock_create_engine.return_value = mock_engine

        expected_df = pd.DataFrame(self.mock_data['data'])
        mock_read_sql.return_value = expected_df

        edw = EDWConnection()
        result = edw.execute_query("SELECT * FROM students")

        # Verify engine was created with correct connection string
        mock_create_engine.assert_called_once()
        conn_string = mock_create_engine.call_args[0][0]
        self.assertIn('mssql+pymssql://testuser:testpass@test.host.com',
                      conn_string)

        # Verify read_sql was called
        mock_read_sql.assert_called_once_with("SELECT * FROM students",
                                              con=mock_connection)

        # Verify result
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)

    @override_settings(
        EDW_USE_MOCK_DATA=False,
        EDW_HOST='test.host.com',
        EDW_USER='testuser',
        EDW_PASS='testpass'
    )
    @patch('training_provisioner.dao.edw.sqlalchemy.create_engine')
    def test_execute_query_sql_error(self, mock_create_engine):
        """Test execute_query with SQL error."""
        mock_create_engine.side_effect = \
            sqlalchemy.exc.SQLAlchemyError("Database connection failed")

        edw = EDWConnection()

        with self.assertRaises(DataAccessException) as context:
            edw.execute_query("SELECT * FROM students")

        self.assertIn("Failed to execute query against EDW",
                      str(context.exception))
        self.assertIn("Database connection failed", str(context.exception))

    @override_settings(
        EDW_USE_MOCK_DATA=False,
        EDW_HOST='test.host.com',
        EDW_USER='testuser',
        EDW_PASS='testpass'
    )
    @patch('training_provisioner.dao.edw.sqlalchemy.create_engine')
    def test_execute_query_unexpected_error(self, mock_create_engine):
        """Test execute_query with unexpected error."""
        mock_create_engine.side_effect = RuntimeError("Unexpected error")

        edw = EDWConnection()

        with self.assertRaises(DataAccessException) as context:
            edw.execute_query("SELECT * FROM students")

        self.assertIn("Unexpected error accessing EDW", str(context.exception))
        self.assertIn("Unexpected error", str(context.exception))

    @override_settings(EDW_USE_MOCK_DATA=True)
    @patch('training_provisioner.dao.edw.inspect.currentframe')
    @patch('training_provisioner.dao.edw.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_get_mock_data_caller_detection(self,
                                            mock_file,
                                            mock_exists,
                                            mock_frame):
        """Test _get_mock_data correctly detects calling function."""
        # Mock frame stack to simulate being called from
        # get_students_from_registration
        mock_caller_frame = MagicMock()
        mock_caller_frame.f_code.co_name = 'get_students_from_registration'
        mock_frame.return_value.f_back.f_back.f_back = mock_caller_frame

        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(self.mock_data)

        edw = EDWConnection()
        _ = edw._get_mock_data("SELECT * FROM test")

        # Should have looked for get_students_from_registration.json
        expected_calls = [call for call in mock_exists.call_args_list
                          if 'get_students_from_registration.json' in str(call)
                          ]
        self.assertTrue(len(expected_calls) > 0)


class ExecuteEDWQueryFunctionTest(TestCase):
    """Test the convenience function execute_edw_query."""

    @override_settings(EDW_USE_MOCK_DATA=True)
    @patch('training_provisioner.dao.edw.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_execute_edw_query_function(self, mock_file, mock_exists):
        """Test the execute_edw_query convenience function."""
        mock_data = {
            "data": [{"student_id": 12345}],
            "columns": ["student_id"],
            "description": "Test data"
        }

        mock_exists.return_value = True
        mock_file.return_value.read.return_value = json.dumps(mock_data)

        result = execute_edw_query("SELECT student_id FROM students")

        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['student_id'], 12345)
