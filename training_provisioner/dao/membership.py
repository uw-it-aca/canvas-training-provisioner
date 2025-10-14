# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from . import is_using_file_dao, mock_file_path
import json


def get_title_vi_membership():
    """
    Return list of integration_ids for Title VI members

    query PDS or whatever system of record for appropriate list of students
    for Title VI training
    """
    if is_using_file_dao():
        with open(mock_file_path("membership.json")) as f:
            return json.load(f)

    return []
