# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.db import models
from django.db.models import F
from training_provisioner.models import ImportResource
from training_provisioner.models.course import Course
from training_provisioner.models.section import Section
from training_provisioner.models.training_course import TrainingCourse
from training_provisioner.exceptions import (
    MissingCourseException, MissingSectionException, EnrollmentCourseMismatch,
    DataAccessException)
from django.utils.timezone import localtime
import re
import logging
import json
import time


logger = logging.getLogger(__name__)


class EnrollmentManager(models.Manager):
    def add_models_for_training_course(self, training_course: TrainingCourse):
        # Entrypoint for model loading for enrollments
        # Studentno will be integration_id in Canvas import.
        start_time = time.time()

        enrollments = []
        # Get student numbers for all currently enrolled students
        # in this course (incl inactive) from existing enrollments
        enrolled_studentnos = set(self.filter(
            course__training_course=training_course
        ).values_list('integration_id', flat=True))

        existing_enrollment_count = len(enrolled_studentnos)

        # Get list of all currently eligible students from EDW
        membership_candidates = training_course.get_course_membership()
        candidate_count = len(membership_candidates)

        # Circuit breaker: if no candidates are found and there are existing
        # enrollments, it may indicate a failure in membership retrieval from
        # EDW. Raise an exception to prevent accidental deletion of enrollments
        if candidate_count == 0 and existing_enrollment_count > 0:
            error_msg = (f"No membership candidates found for "
                         f"{training_course.course_name} but "
                         f"{existing_enrollment_count} existing enrollments "
                         f"present. This may indicate a membership retrieval "
                         f"failure from EDW.")
            logger.error(error_msg)
            raise DataAccessException(error_msg)

        # Filter candidates based on course type and enrollments in other
        # courses. If current course type is '101', exclude students with
        # previous '101' enrollments from different academic years and
        # vice versa for booster courses.
        # Note: this will filter based on active enrollments in other courses
        # There is potentially a race condition here based on a student being
        # reenrolled in another course, so courses should always be processed
        # in ascending order of academic year to minimize this.
        filtered_candidates = self._filter_candidates_by_course_type(
            membership_candidates, training_course)

        # Count enrollments added and dropped for metrics
        enrollments_added = 0
        enrollments_dropped = 0

        # Iterate through filtered candidates and add/update enrollments,
        # removing from enrolled_studentnos set as we go
        for studentno in filtered_candidates:
            studentno = str(studentno)  # Ensure type consistency
            try:
                enrollment = self._add_enrollment(studentno, training_course)
                enrollments.append(enrollment)
                enrolled_studentnos.discard(studentno)
                enrollments_added += 1
            except EnrollmentCourseMismatch as ex:
                logger.error(ex)

        # cull dropped members who appear in the course but not in the
        # filtered candidate list
        now = localtime()
        for dropped_studentno in enrolled_studentnos:
            try:
                enrollment = Enrollment.objects.get(
                    integration_id=dropped_studentno,
                    course__training_course=training_course)
                if enrollment.deleted_date is not None:
                    # already marked as deleted
                    continue
                enrollment.deleted_date = now
                enrollment.priority = ImportResource.PRIORITY_DEFAULT
                enrollment.save()
                enrollments.append(enrollment)
                enrollments_dropped += 1

                self._trigger_course_import(enrollment.course)

                drop_id = (enrollment.section.section_id
                           if enrollment.section
                           else enrollment.course.course_id)
                logger.info(f"delete enrollment {dropped_studentno} "
                            f"from {drop_id}")

            except Enrollment.DoesNotExist:
                logger.info("Missing dropped enrollment: "
                            f"{dropped_studentno} from {training_course}")

        # Calculate timing and log metrics
        end_time = time.time()
        duration = end_time - start_time

        # Log metrics
        metrics = {
            "training_course": training_course.course_name,
            "duration_seconds": round(duration, 3),
            "existing_enrollments": existing_enrollment_count,
            "candidates_from_edw": candidate_count,
            "enrollments_added": enrollments_added,
            "enrollments_dropped": enrollments_dropped,
            "timestamp": localtime().isoformat()
        }

        logger.info(f"Enrollment processing completed for "
                    f"{training_course.course_name}: "
                    f"{candidate_count} candidates found, "
                    f"{enrollments_added} processed, {enrollments_dropped} "
                    f"dropped in {duration:.3f}s")

        # Write metrics to output file in /tmp
        try:
            metrics_file = "/tmp/enrollment_metrics_"
            f"{training_course.course_name.replace(' ', '_')}.json"
            with open(metrics_file, 'w') as f:
                json.dump(metrics, f, indent=2)
        except Exception as ex:
            logger.warning(f"Failed to write metrics file: {ex}")

        return enrollments

    def _filter_candidates_by_course_type(self, candidates, training_course):
        """
        Filter candidate list based on course type and previous enrollment
        history.

        NOTE: with the has_previous_101_enrollment logic a student who had an
        enrollment in the previous year which was deleted would be treated as
        NOT having a previous enrollment and therefore be eligible for 101 and
        ineligible for booster. This is desirable for students who dropped
        before census day, but might not be for students who were dropped
        after census.

        Args:
            candidates (list): List of student integration_ids
            training_course: TrainingCourse instance

        Returns:
            list: Filtered list of candidates
        """

        filtered_candidates = []

        for studentno in candidates:
            has_previous_101_enrollment = self._has_previous_101_enrollment(
                studentno, training_course)
            has_same_year_enrollment = self.\
                _has_enrollment_in_same_academic_year(
                    studentno, training_course)

            if training_course.course_type == TrainingCourse.COURSE_TYPE_101:
                # For 101 courses:
                # 1. Exclude students who already have enrollment in same
                #   academic year
                # 2. Exclude students who have previous 101 enrollment from
                #   different academic year
                if has_same_year_enrollment:
                    logger.debug(f"Excluding {studentno} from 101 course - "
                                 f"already enrolled in same academic year")
                elif has_previous_101_enrollment:
                    logger.debug(f"Excluding {studentno} from 101 course - "
                                 f"has previous 101 enrollment from different "
                                 f"academic year")
                else:
                    filtered_candidates.append(studentno)

            elif training_course.course_type == \
                    TrainingCourse.COURSE_TYPE_BOOSTER:
                # For booster courses:
                # 1. Exclude students who already have enrollment in same
                #   academic year
                # 2. Only include students who have previous 101 enrollment
                #   from different academic year
                if has_same_year_enrollment:
                    logger.debug(f"Excluding {studentno} from booster course -"
                                 f" already enrolled in same academic year")
                elif has_previous_101_enrollment:
                    filtered_candidates.append(studentno)
                else:
                    logger.debug(f"Excluding {studentno} from booster "
                                 f"course - no previous 101 enrollment from "
                                 f"different academic year")
            else:
                # For unknown course types, include all candidates
                filtered_candidates.append(studentno)

        logger.info(f"Filtered candidates for "
                    f"{training_course.course_name} "
                    f"({training_course.course_type}): "
                    f"{len(filtered_candidates)} of {len(candidates)} "
                    f"candidates")

        return filtered_candidates

    def _get_academic_year(self, term_id):
        """
        Extract academic year from term_id.

        Args:
            term_id (str): Term identifier like 'AY2025-2026-101' or
                'AY2025-2026-B'

        Returns:
            str: Academic year portion like 'AY2025-2026'
        """

        term_parts = re.match(r"^AY(\d{4})-(\d{4})(-.*)?$", term_id)
        if not term_parts:
            raise ValueError(
                f"Invalid term_id format: {term_id}")
        return f"AY{term_parts.group(1)}-{term_parts.group(2)}"

    def _has_enrollment_in_same_academic_year(self,
                                              studentno,
                                              current_training_course):
        """
        Check if a student has any active enrollment in the same academic year
        as the current training course.

        Args:
            studentno (str): Student number (integration_id to Canvas)
            current_training_course: Current TrainingCourse instance

        Returns:
            bool: True if student has enrollment in same academic year,
                False otherwise
        """
        current_academic_year = self._get_academic_year(
            current_training_course.term_id)

        # Check for any active enrollment in the same academic year
        same_year_enrollments = self.filter(
            integration_id=studentno,
            deleted_date__isnull=True
        ).exclude(
            # Exclude current course
            course__training_course=current_training_course
        )

        for enrollment in same_year_enrollments:
            enrollment_academic_year = self._get_academic_year(
                enrollment.course.training_course.term_id)
            if enrollment_academic_year == current_academic_year:
                return True

        return False

    def _has_previous_101_enrollment(self, studentno, current_training_course):
        """
        Check if a student has any previous active enrollment in a '101'
        type course from a DIFFERENT academic year than the current
        training course.

        Args:
            studentno (str): Student number (integration_id to Canvas)
            current_training_course: Current TrainingCourse instance

        Returns:
            bool: True if student has previous 101 enrollment from different
            academic year, False otherwise
        """

        # Get current term_id (e.g., 'AY2025-2026-101')
        current_term_id = current_training_course.term_id

        # Get all training courses with course_type='101' where
        # student has active enrollment. Exclude enrollments from the same
        # term_id (same academic year)
        previous_101_enrollments = self.filter(
            integration_id=studentno,
            deleted_date__isnull=True,
            course__training_course__course_type=TrainingCourse.COURSE_TYPE_101
        ).exclude(
            course__training_course__term_id=current_term_id
        ).exists()

        return previous_101_enrollments

    def _add_enrollment(self, studentno, training_course):
        # Add or update enrollment for a given student in the training course
        try:
            course_id = training_course.get_course_id_for_member(studentno)
            course = Course.objects.get(course_id=course_id)
            section_id = course.get_section_id_for_member(studentno)
            section = (Section.objects.get(section_id=section_id)
                       if section_id is not None else None)
            # priority = Enrollment.PRIORITY_DEFAULT

            enrollment = Enrollment.objects.get(
                integration_id=studentno,
                course__training_course=training_course)

            # Check if this is a reenrollment (previously deleted user)
            if enrollment.deleted_date is not None:
                # This student has a previously deleted enrollment in this
                # course. Reactivate it as a reenrollment
                enrollment.deleted_date = None
                enrollment.priority = ImportResource.PRIORITY_DEFAULT
                enrollment.save()
                self._trigger_course_import(enrollment.course)
                section_or_course_id = enrollment.section.section_id if \
                    enrollment.section else enrollment.course.course_id
                logger.info(f"reactivate enrollment {studentno} in "
                            f"{section_or_course_id}")

            if enrollment.course != course:
                raise EnrollmentCourseMismatch(
                    f"Enrollment for {studentno} course change from "
                    f"{enrollment.course} to {course} NOT allowed")
            elif enrollment.section != section:
                orig_course_id = enrollment.course.course_id
                orig_section_id = (enrollment.section.section_id
                                   if enrollment.section else None)
                # deactivate old enrollment
                enrollment.deleted_date = localtime()
                enrollment.priority = ImportResource.PRIORITY_DEFAULT
                enrollment.save()

                # reactivate prior enrollment or create new one
                enrollment = Enrollment.objects.get(
                    integration_id=studentno, course=course, section=section)
                enrollment.deleted_date = None
                enrollment.priority = ImportResource.PRIORITY_DEFAULT
                enrollment.save()

                logger.info(
                    f"Enrollment for {studentno} in "
                    f"{training_course.course_id_prefix} CHANGED from course "
                    f"{orig_course_id} to {course_id}, section "
                    f"{orig_section_id} to {section_id}")

        except Course.DoesNotExist:
            raise MissingCourseException(
                f"Enrollment for {studentno} in "
                f"{training_course.course_id_prefix} missing course model "
                f"for: {course_id}")
        except Section.DoesNotExist:
            raise MissingSectionException(
                f"Enrollment for {studentno} in "
                f"{training_course.course_id_prefix} missing section model "
                f"for: {section_id}")
        except Enrollment.DoesNotExist:
            enrollment = Enrollment.objects.create(
                integration_id=studentno, course=course, section=section)
            self._trigger_course_import(course)
            logger.info(f"create enrollment {studentno} in "
                        f"{section_id if section_id else course_id}")

        return enrollment

    def _trigger_course_import(self, course):
        # bump course import priority to signal cascading import
        if course.priority == Course.PRIORITY_NONE:
            course.priority = course.PRIORITY_DEFAULT
            course.save()

    def get_models_for_training_course(self, training_course):
        return self.filter(course__training_course=training_course,
                           deleted_date__isnull=True)

    def course_imports(self, course):
        pks = super(EnrollmentManager, self).get_queryset().filter(
            course=course.id,
            priority__gt=ImportResource.PRIORITY_NONE,
            queue_id__isnull=True
        ).values_list('pk', flat=True)

        super(EnrollmentManager, self).get_queryset().filter(
            pk__in=list(pks)).update(queue_id=course.queue_id)

        return super(EnrollmentManager, self).get_queryset().filter(
            pk__in=list(pks))

    def queued(self, queue_id):
        return super(EnrollmentManager, self).get_queryset().filter(
            queue_id=queue_id)

    def dequeue(self, sis_import):
        if sis_import.is_imported():
            # Decrement the priority
            super(EnrollmentManager, self).get_queryset().filter(
                queue_id=sis_import.pk, priority__gt=Enrollment.PRIORITY_NONE
            ).update(
                queue_id=None, priority=F('priority') - 1)
        else:
            self.queued(sis_import.pk).update(queue_id=None)


class Enrollment(ImportResource):
    """
    Represents a user's Course enrollment event to be processed.
    """
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    section = models.ForeignKey(Section, null=True, on_delete=models.CASCADE)
    integration_id = models.CharField(max_length=8, db_index=True)
    created_date = models.DateTimeField(auto_now=True)
    provisioned_date = models.DateTimeField(null=True)
    deleted_date = models.DateTimeField(null=True)
    priority = models.SmallIntegerField(
        default=ImportResource.PRIORITY_DEFAULT,
        choices=ImportResource.PRIORITY_CHOICES)
    queue_id = models.CharField(max_length=30, null=True)

    objects = EnrollmentManager()

    @property
    def is_active(self):
        return self.deleted_date is None

    def json_data(self):
        return {
            'course': self.course.json_data(),
            'section': self.section.json_data() if self.section else None,
            'integration_id': self.integration_id,
            'created_date': localtime(self.created_date).isoformat(),
            'provisioned_date': localtime(
                self.provisioned_date).isoformat() if (
                    self.provisioned_date) else None,
            'is_active': self.is_active,
            'deleted_date': localtime(self.deleted_date).isoformat() if (
                self.deleted_date) else None,
        }

    def __str__(self):
        return json.dumps(self.json_data())

    class Meta:
        db_table = 'enrollment'
        unique_together = ('integration_id', 'course', 'section')
