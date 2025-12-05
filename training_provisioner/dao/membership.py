# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from . import mock_file_path
import json
import re
import logging
from training_provisioner.dao.edw import execute_edw_query

logger = logging.getLogger(__name__)


def test_membership(training_course):
    """
    Return list of integration_ids for testing
    """
    try:
        with open(mock_file_path("membership.json")) as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"test membership: {e}")

    return []


def title_vi_membership_candidates(training_course):
    """
    Query SDB for appropriate list of students for the supplied Title VI
    training course.

    This query will return a list of eligible students, but the business logic
    for determining who should be enrolled in a given training course will be
    handled on a student by student basis in the EnrollmentManager since
    enrollment depends on past enrollments.

    Enrollment manager will also need to check for dropped students, as they
    will need to be marked as inactive in the training course.

    Args:
        training_course (TrainingCourse): training course object

    Returns:
        list: integration_ids of eligible students
    """
    eligible_members = []

    # Use term_id to determine academic year
    term_parts = re.match(r"^AY(\d{4})-(\d{4})$", training_course.term_id)
    if not term_parts:
        raise ValueError(
            f"Invalid term_id format: {training_course.term_id}")
    training_course_academic_year = f"{term_parts.group(1)}/{term_parts.group(2)}"

    # Note: overriding the first Title VI 101 course to only get Spring 2026,
    # but otherwise we should get all quarters in the academic year to avoid
    # dropping students who stop attending later in the year...
    start_quarter = None
    if training_course_academic_year == '2025/2026':
        start_quarter = 20262  # Spring 2026 only for AY25-26 course
    quarters_in_ay = get_quarters_in_ay(training_course_academic_year,
                                        start_quarter)
    for quartercode in quarters_in_ay:
        quarter_info = get_info_for_quarter(quartercode)
        for student_id in get_students_from_registration(quartercode):
            if student_id not in eligible_members:
                eligible_members.append(student_id)
        if quarter_info['censusDayStatus'] == 'Before Census Day':
            for student_id in get_students_from_admissions(quartercode):
                if student_id not in eligible_members:
                    eligible_members.append(student_id)

    return eligible_members


def title_vi_booster_membership_candidates(training_course):
    """
    Booster course membership candidates are the same as the main Title VI
    course.

    Args:
        training_course (TrainingCourse): training course object

    Returns:
        list: integration_ids of eligible students
    """
    return title_vi_membership_candidates(training_course)


def get_quarters_in_ay(academic_year, current_quarter_code):
    """
    Given an academic year string like "2023/2024" and a current quarter
    like "20254", return list of quarters in that academic year occurring
    on or after the current quarter, if a quarter code is specified or all
    quarters if not.

    NOTE: At a project level we will use official UW academic year
    (SUM-SPR)
    See: https://metadata.uw.edu/catalog/viewitem/Term/studentdata.academicyear

    Args:
        academic_year (str): academic year in "YYYY/YYYY" format
        current_quarter_code (str|int|None): current quarter code like
            "20254"

    Returns:
        list: quarter codes in the academic year on or after current quarter,
            eg, ['20261', '20262', '20263', '20264']
    """
    ay_parts = re.match(r"^(\d{4})/(\d{4})$", academic_year)
    if not ay_parts:
        raise ValueError(f"Invalid academic_year format: {academic_year}")

    year1, year2 = ay_parts[1], ay_parts[2]
    quarters = [f"{year1}3", f"{year1}4", f"{year2}1", f"{year2}2"]

    if current_quarter_code is None:
        return quarters

    # Find the index of the current quarter, or return empty if past this AY
    # return all if before this AY
    try:
        start_idx = quarters.index(str(current_quarter_code))
        return quarters[start_idx:]
    except ValueError:
        # Current quarter not in this AY - return empty if it's past,
        # all if before
        return ([] if int(current_quarter_code) > int(quarters[-1])
                else quarters)


def get_current_quarter_info():
    """
    Return dict with info about the current quarter based on today's date

    Returns:
    dict: info about the current quarter, eg:
        {'AcademicContigYrQtrCode': '20254',
        'AcademicYrName': '2025/2026',
        'CensusDayStatus': 'After Census Day'}
    """
    query = """
        SELECT
            d.AcademicContigYrQtrCode,
            d.AcademicYrName,
            CASE
                WHEN d.CalendarDate < cd.CalendarDate THEN 'Before Census Day'
                WHEN d.CalendarDate = cd.CalendarDate THEN 'On Census Day'
                ELSE 'After Census Day'
            END AS CensusDayStatus
        FROM EDWPresentation.sec.dimDate d
        LEFT JOIN EDWPresentation.sec.dimDate cd
            ON d.AcademicContigYrQtrCode = cd.AcademicContigYrQtrCode
            AND cd.AcademicQtrCensusDayInd = 'Y'
        WHERE d.CalendarDate = CONVERT(DATE, GETDATE())
    """
    df = execute_edw_query(query)
    return df.iloc[0].to_dict()


def get_info_for_quarter(quarter_code):
    """
    Given a quarter code like "20254", return dict with info about that quarter

    Args:
        quarter_code (str|int): quarter code like "20254"
    Returns:
        dict: info about the quarter, eg:
            {'AcademicContigYrQtrCode': '20254',
            'AcademicYrName': '2025/2026',
            'CensusDayStatus': 'After Census Day'}
    """
    if not re.match(r"^\d{5}$", str(quarter_code)):
        raise ValueError(f"Invalid quarter_code format: {quarter_code}")

    query = f"""
        DECLARE @acaQtr INT = {quarter_code};
        SELECT
            d.AcademicContigYrQtrCode,
            d.AcademicYrName,
            CASE
                WHEN CONVERT(DATE, GETDATE()) < cd.CalendarDate
                    THEN 'Before Census Day'
                WHEN CONVERT(DATE, GETDATE()) = cd.CalendarDate
                    THEN 'On Census Day'
                ELSE 'After Census Day'
            END AS CensusDayStatus
        FROM EDWPresentation.sec.dimDate d
        LEFT JOIN EDWPresentation.sec.dimDate cd
            ON d.AcademicContigYrQtrCode = cd.AcademicContigYrQtrCode
            AND cd.AcademicQtrCensusDayInd = 'Y'
        WHERE d.AcademicContigYrQtrCode = @acaQtr
            AND d.AcademicQtrCensusDayInd = 'Y'
    """
    df = execute_edw_query(query)
    return df.iloc[0].to_dict()


def get_students_from_registration(quarter_code):
    """
    Given a quarter code like "20254", return list of integration_ids
    for students registered in that quarter.

    Args:
        quarter_code (str|int): quarter code like "20254"
    Returns:
        list: student_numbers of registered students
    """
    if not re.match(r"^\d{5}$", str(quarter_code)):
        raise ValueError(f"Invalid quarter_code format: {quarter_code}")

    query = f"""
        DECLARE @acaQtr INT = {quarter_code};
        SELECT s.student_no AS StudentNumber
        FROM UWSDBDataStore.sec.registration rc
        INNER JOIN UWSDBDataStore.sec.student_1 s
            ON rc.system_key = s.system_key
        WHERE ((rc.regis_yr * 10) + rc.regis_qtr) = @acaQtr
            AND s.student_no > 0
            AND rc.enroll_status = 12
            AND rc.regis_class NOT IN (6, 9, 10)
    """
    df = execute_edw_query(query)
    return df['StudentNumber'].tolist()


def get_students_from_admissions(quarter_code):
    """
    Given a quarter code like "20254", return list of integration_ids
    for students admitted for that quarter.

    Args:
        quarter_code (str|int): quarter code like "20254"

    Returns:
        list: student_numbers of admitted students
    """
    if not re.match(r"^\d{5}$", str(quarter_code)):
        raise ValueError(f"Invalid quarter_code format: {quarter_code}")

    query = f"""
        DECLARE @acaQtr INT = {quarter_code};
        SELECT s1.student_no AS StudentNumber
        FROM UWSDBDataStore.sec.student_1 s1
        INNER JOIN UWSDBDataStore.sec.sr_adm_appl aa
            ON s1.system_key = aa.system_key
            AND s1.admitted_for_yr = aa.appl_yr
            AND s1.admitted_for_qtr = aa.appl_qtr
            AND aa.appl_type != 'N'
            AND aa.appl_status IN (15, 16)
        WHERE s1.student_no > 0
            AND (s1.admitted_for_yr * 10 + s1.admitted_for_qtr) = @acaQtr
    """

    quarter_info = get_info_for_quarter(quarter_code)
    if quarter_info['CensusDayStatus'] != 'After Census Day':
        # We will only return students from the admissions table if
        # census day has not yet occurred for the supplied quarter
        # otherwise we would expect to find them via registration
        df = execute_edw_query(query)
        return df['StudentNumber'].tolist()
    else:
        return []
