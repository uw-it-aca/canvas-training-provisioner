# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

import os


def mock_file_path(filename):
    current_dir = os.path.dirname(os.path.realpath(__file__))
    return os.path.abspath(os.path.join(
        current_dir, "..", "data", filename))
