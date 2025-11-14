# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from . import is_using_file_dao, mock_file_path
import json


def test_membership(training_course):
    """
    Return list of integration_ids for testing
    """
    if is_using_file_dao():
        with open(mock_file_path("membership.json")) as f:
            return json.load(f)

    return []


def title_vi_membership(training_course):
    """
    Return list of integration_ids for Title VI members

    query PDS or whatever system of record for appropriate list of students
    for Title VI training
    """

    # sniff at training_course course_id or term_id or whatever to
    # determine appropriate membership
    return []


def title_vi_booster_membership(training_course):
    """
    Return list of integration_ids for Title VI members

    query PDS or whatever system of record for appropriate list of students
    for Title VI training
    """

    # sniff at training_course course_id or term_id or whatever to
    # determine appropriate membership
    return []
