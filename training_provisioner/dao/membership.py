# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from . import mock_file_path
import json
import os
import re
import logging
from training_provisioner.dao.edw import execute_edw_query

logger = logging.getLogger(__name__)


class MemberList:
    """
    Class to represent a list of members eligible for a training course.
    """
    def __init__(self):
        self._members = {}

    def add_members(self, members: list[str], qtrcode: str, regtype: str):
        """
        Add members with eligible terms for a training course.

        Args:
            members (list): list of member IDs to add
            qtrcode (str): quarter code to associate with these members
            regtype (str): registration type, either "R" ('registration')
            or 'A' ('admissions')
        """
        if members is None:
            return

        regtype = regtype.upper() if regtype else ''

        try:
            for member in members:
                if member not in self._members:
                    self._members[member] = set()
                self._members[member].add(qtrcode+regtype)
        except TypeError as e:
            raise TypeError(f"members must be an iterable, got "
                            f"{type(members).__name__}") from e

    def to_dict(self):
        """
        Convert the member list to a dictionary mapping member IDs to lists of
        eligible course codes.

        Returns:
            dict: mapping of member IDs to lists of course codes
        """
        return {member: sorted(courses)
                for member, courses in self._members.items()}


def test_membership(training_course):
    """
    Return dictionary mapping integration_ids to eligible terms for testing
    """
    try:
        with open(mock_file_path("membership.json")) as f:
            member_list = json.load(f)
            if isinstance(member_list, dict):
                return member_list
            # Convert list to dictionary format with mock terms
            return {member: ["20254R", "20261R"] for member in member_list}
    except Exception as e:
        logger.error(f"test membership: {e}")

    return {}


def title_vi_membership_candidates(training_course) -> dict[str, list[str]]:
    """
    Query SDB for appropriate list of students for the supplied Title VI
    training course.

    This query will return a dictionary mapping eligible students to the terms
    in which they were found eligible, but the business logic for determining
    who should be enrolled in a given training course will be handled on a
    student by student basis in the EnrollmentManager since enrollment depends
    on past enrollments.

    Enrollment manager will also need to check for dropped students, as they
    will need to be marked as inactive in the training course.

    Args:
        training_course (TrainingCourse): training course object

    Returns:
        dict: mapping of integration_ids to eligible terms, e.g.
              {"1234567": ["20254A", "20261R"], "2345678": ["20262A"]}
    """
    eligible_members_with_terms = MemberList()

    quarter_stats = {}

    # Use term_id to determine academic year. Term SIS IDs may include a
    # suffix after the standard AYYYYY-YYYY format, so we ignore that here.
    # term_id is assumed to be term.sis_source_id
    term_parts = re.match(r"^AY(\d{4})-(\d{4})(-.*)?$",
                          training_course.term_id)
    if not term_parts:
        raise ValueError(
            f"Invalid term_id format: {training_course.term_id}")
    training_course_academic_year = \
        f"{term_parts.group(1)}/{term_parts.group(2)}"

    # Note: overriding the first Title VI 101 course to only get Spring 2026,
    # (PROD only) but otherwise we should get all quarters in the academic
    # year to avoid dropping students who stop attending later in the year...
    start_quarter = None
    if training_course_academic_year == '2025/2026' and \
       os.getenv('CANVAS_ENV') != 'EVAL':
        start_quarter = 20262  # Spring 2026 **only** for AY25-26 course
    quarters_in_ay = get_quarters_in_ay(training_course_academic_year,
                                        start_quarter)

    # --------------------------
    # Iterate over quarters in the academic year and gather students from EDW
    # registration and optionally admissions tables (depending on census day).

    # We will track the quarters in which each student is found to be eligible
    # and store that in the Enrollment for future reporting and forensics.

    # We will append an 'R' or 'A' to the quarter code to indicate whether the
    # student was found in registration or admissions tables, respectively.
    # ---------------------------

    for quartercode in quarters_in_ay:
        quarter_info = get_info_for_quarter(quartercode)
        registration_students = get_students_from_registration(quartercode)
        admissions_students = []

        # Track registration students with terms
        eligible_members_with_terms.add_members(
            registration_students, str(quartercode), 'R')

        if quarter_info['CensusDayStatus'] == 'Before Census Day':
            # We will only add students from the admissions table if
            # census day has not yet occurred for the supplied quarter
            # otherwise we would expect to find them via registration
            admissions_students = get_students_from_admissions(quartercode)
            eligible_members_with_terms.add_members(
                admissions_students, str(quartercode), 'A')

        # Track statistics for this quarter
        quarter_stats[quartercode] = {
            'registration_count': len(registration_students),
            'admissions_count': len(admissions_students),
            'census_day_status': quarter_info['CensusDayStatus']
        }

    # Write debug files for auditing purposes
    _write_debug_files(training_course.term_id,
                       set(eligible_members_with_terms.to_dict().keys()),
                       quarter_stats, True)

    return eligible_members_with_terms.to_dict()


def title_vi_booster_membership_candidates(training_course):
    """
    Booster course membership candidates are the same as the main Title VI
    course.

    Args:
        training_course (TrainingCourse): training course object

    Returns:
        dict: mapping of integration_ids to eligible terms
    """
    return title_vi_membership_candidates(training_course)


def get_quarters_in_ay(academic_year, current_quarter_code):
    """
    Given an academic year string like "2023/2024" and a current quarter
    like "20254", return list of quarters in that academic year occurring
    on or after the current quarter, if a quarter code is specified or all
    quarters if not.

    NOTE: At a project level we will use official UW academic year
    (Summer, Autumn, Winter, Spring)
    See: https://metadata.uw.edu/catalog/viewitem/Term/studentdata.academicyear

    Args:
        academic_year (str): academic year in "YYYY/YYYY" format
        current_quarter_code (str|int|None): current quarter code like
            "20254"

    Returns:
        list: quarter codes in the academic year on or after current quarter,
            eg, ['20253', '20254', '20261', '20262']
    """
    ay_parts = re.match(r"^(\d{4})/(\d{4})$", academic_year)
    if not ay_parts:
        raise ValueError(f"Invalid academic_year format: {academic_year}")

    year1, year2 = ay_parts.group(1), ay_parts.group(2)
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


def get_students_from_registration(quarter_code) -> list[str]:
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
        SELECT s1.student_no AS StudentNumber
        FROM UWSDBDataStore.sec.registration rc
        INNER JOIN UWSDBDataStore.sec.student_1 s1
            ON rc.system_key = s1.system_key
        WHERE ((rc.regis_yr * 10) + rc.regis_qtr) = @acaQtr
            AND s1.student_no > 0
            AND rc.enroll_status = 12
            AND rc.regis_class NOT IN (6, 9, 10)
            AND s1.deceased_dt IS NULL
    """
    df = execute_edw_query(query)
    return df['StudentNumber'].astype(str).str.zfill(7).tolist()


def get_students_from_admissions(quarter_code) -> list[str]:
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
        WHERE s1.student_no > 0
            AND aa.appl_type != 'N'
            AND aa.appl_status IN (15, 16)
            AND s1.deceased_dt IS NULL
            AND (s1.admitted_for_yr * 10 + s1.admitted_for_qtr) = @acaQtr
    """

    df = execute_edw_query(query)
    return df['StudentNumber'].astype(str).str.zfill(7).tolist()


def _write_debug_files(term_id,
                       eligible_members,
                       quarter_stats,
                       stats_only=False):
    """
    Write debug and audit files for membership analysis.

    Args:
        term_id (str): Training course term ID
        eligible_members (set): Set of eligible student IDs
        quarter_stats (dict): Statistics for each quarter
        stats_only (bool): If True, only write statistics file
    """
    from datetime import datetime

    # Create safe filename from term_id
    safe_term_id = re.sub(r'[^a-zA-Z0-9\-]', '_', term_id)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    try:
        if not stats_only:
            # Write eligible members list
            members_filename = "/tmp/training_eligible_members_" \
                f"{safe_term_id}_{timestamp}.txt"
            with open(members_filename, 'w') as f:
                f.write(f"# Eligible members for training course: {term_id}\n")
                f.write(f"# Generated: {datetime.now().isoformat()}\n")
                f.write(f"# Total count: {len(eligible_members)}\n\n")
                for member_id in sorted(eligible_members):
                    f.write(f"{member_id}\n")

            logger.info(f"Wrote eligible members list to: {members_filename}")

        # Write quarter statistics
        stats_filename = "/tmp/training_quarter_stats_"\
            f"{safe_term_id}_{timestamp}.txt"
        with open(stats_filename, 'w') as f:
            f.write(f"# Quarter statistics for training course: {term_id}\n")
            f.write(f"# Generated: {datetime.now().isoformat()}\n\n")
            f.write(f"{'Quarter':<10} {'Registration':<12} {'Admissions':<12}"
                    f" {'Census Status'}\n")
            f.write("-" * 70 + "\n")

            total_registration = 0
            total_admissions = 0

            for quarter, stats in sorted(quarter_stats.items()):
                f.write(f"{quarter:<10} {stats['registration_count']:<12} "
                        f"{stats['admissions_count']:<12}"
                        f"{stats['census_day_status']}\n")
                total_registration += stats['registration_count']
                total_admissions += stats['admissions_count']

            f.write("-" * 70 + "\n")
            f.write(f"{'TOTAL':<10} {total_registration:<12}"
                    f"{total_admissions:<12}\n")
            f.write(f"\nUnique eligible members: {len(eligible_members)}\n")

        logger.info(f"Wrote quarter statistics to: {stats_filename}")

    except Exception as e:
        logger.error(f"Failed to write debug files for {term_id}: {e}")
