# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

import sqlalchemy
import pandas as pd
import time
import logging
import inspect
import json
import os
from urllib.parse import quote_plus
from django.conf import settings
from training_provisioner.exceptions import DataAccessException

logger = logging.getLogger(__name__)


class EDWConnection:
    """
    Enterprise Data Warehouse connection class for executing SQL queries
    and returning results as Pandas DataFrames.

    Supports mock data for local development environments.
    See README for details.
    """

    def __init__(self):
        """Initialize EDW connection parameters from Django settings."""
        self.use_mock_data = getattr(settings, 'EDW_USE_MOCK_DATA', False)

        if self.use_mock_data:
            logger.info("EDW configured for mock data in localdev environment")
            return

        self.host = getattr(settings, 'EDW_HOST', None)
        # note: username contains a "\" which needs to be handled properly
        self.user = getattr(settings, 'EDW_USER', None)
        self.password = getattr(settings, 'EDW_PASS', None)

        if not all([self.host, self.user, self.password]):
            raise ValueError(
                "EDW connection parameters (EDW_HOST, EDW_USER, EDW_PASS) "
                "must be configured in settings")

    def _get_connection_string(self):
        """Build the SQLAlchemy connection string for EDW."""
        return (f"mssql+pymssql://{quote_plus(self.user)}:"
                f"{quote_plus(self.password)}@{self.host}:1433")

    def execute_query(self, query):
        """
        Execute a SQL query against the EDW and return results as a
        Pandas DataFrame.

        Args:
            query (str): SQL query to execute

        Returns:
            pandas.DataFrame: Query results

        Raises:
            DataAccessException: If there's an error connecting or executing
                the query
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        # In localdev environment, return mock data instead of executing
        # real queries
        if self.use_mock_data:
            return self._get_mock_data(query)

        logger.info(f"{'*'*40}\nConnecting to EDW at {self.host}")
        logger.debug(f"Executing query: {query[:100]}"
                     f"{'...' if len(query) > 100 else ''}")

        connection_string = self._get_connection_string()

        try:
            engine = sqlalchemy.create_engine(connection_string)
            start_time = time.time()

            with engine.connect() as conn:
                data = pd.read_sql(query, con=conn)

            elapsed_time = time.time() - start_time
            logger.info(f"\tData read from {self.host}: {data.shape} "
                        f"(rows, columns)")
            logger.info(f"\tElapsed time: {elapsed_time:.2f}s\n{'*'*40}")

            return data

        except sqlalchemy.exc.SQLAlchemyError as e:
            logger.error(f"Database error executing query: {e}")
            raise DataAccessException(
                f"Failed to execute query against EDW: {e}")
        except Exception as e:
            logger.error(f"Unexpected error reading data from EDW: {e}")
            raise DataAccessException(f"Unexpected error accessing EDW: {e}")

    def _get_mock_data(self, query):
        """
        Return mock data for localdev environment based on calling function

        Args:
            query (str): SQL query (not used, kept for compatibility)

        Returns:
            pandas.DataFrame: Mock data appropriate for the calling function
        """
        logger.info("EDW: Returning mock data for localdev environment")

        # Get the name of the calling function
        # Skip execute_query frame
        caller_frame = inspect.currentframe().f_back.f_back.f_back
        caller_function = (caller_frame.f_code.co_name
                           if caller_frame else 'unknown')

        logger.debug(f"EDW mock data requested by function: "
                     f"{caller_function}")

        # Load mock data from JSON file based on function name
        mock_data_dir = os.path.join(
            os.path.dirname(__file__),
            '..', 'data', 'edw_mock'
        )

        # Try to find a specific mock file for the calling function
        mock_file = os.path.join(mock_data_dir, f"{caller_function}.json")

        if not os.path.exists(mock_file):
            # Fallback to default mock data
            logger.warning(f"No mock data file found for function "
                           f"'{caller_function}', using default")
            mock_file = os.path.join(mock_data_dir, "default.json")

        try:
            with open(mock_file, 'r') as f:
                mock_data = json.load(f)

            logger.info(f"Loaded mock data from "
                        f"{os.path.basename(mock_file)}: "
                        f"{mock_data.get('description', 'No description')}")

            # Convert to DataFrame
            if mock_data.get('data'):
                return pd.DataFrame(mock_data['data'])
            else:
                return pd.DataFrame()

        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error loading mock data from {mock_file}: {e}")
            return pd.DataFrame()


def execute_edw_query(query):
    """
    Convenience function to execute a query against the EDW.

    Args:
        query (str): SQL query to execute

    Returns:
        pandas.DataFrame: Query results
    """
    edw = EDWConnection()
    return edw.execute_query(query)
