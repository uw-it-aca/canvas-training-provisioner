# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.core.management.base import BaseCommand, CommandError
from training_provisioner.models.training_course import TrainingCourse
from training_provisioner.models.course import Course
from training_provisioner.dao.canvas import (unpublish_course_by_sis_id,
                                             publish_course_by_sis_id)
from logging import getLogger

logger = getLogger(__name__)


class Command(BaseCommand):
    help = "Publish or unpublish Canvas courses associated with the specified "
    "training course."

    def add_arguments(self, parser):
        parser.add_argument(
            '--training-course-blueprint-sis-id',
            type=str,
            help='Publish or unpublish courses for the specified training'
            ' course blueprint SIS ID.',
            required=True
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show which courses would be modified without actually'
            ' publishing or unpublishing them'
        )
        parser.add_argument(
            '--unpublish',
            action='store_true',
            help='Unpublish the courses instead of publishing them'
        )

    def handle(self, *args, **options):
        training_course_blueprint_sis_id = options[
            'training-course-blueprint-sis-id']
        dry_run = options.get('dry_run', False)
        unpublish = options.get('unpublish', False)

        try:
            # Get the training course
            training_course = TrainingCourse.objects.get(
                blueprint_course_id=training_course_blueprint_sis_id)
            self.stdout.write(
                f"Processing training course: {training_course}")

            # Get all courses associated with this training course
            courses = Course.objects.get_models_for_training_course(
                training_course)

            if not courses.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"No courses found for training course based on "
                        f"{training_course_blueprint_sis_id}"))
                return

            self.stdout.write(f"Found {courses.count()} courses to "
                              f"{'unpublish' if unpublish else 'publish'}")

            modified_courses_count = 0
            failed_count = 0

            for course in courses:
                course_sis_id = course.course_id
                action_taken = 'unpublish' if unpublish else 'publish'

                if dry_run:
                    self.stdout.write(f"Would {action_taken} course:"
                                      f" {course_sis_id}")
                    continue

                try:
                    if unpublish:
                        self.stdout.write("Unpublishing course: "
                                          f"{course_sis_id}")
                        result = unpublish_course_by_sis_id(course_sis_id)
                    else:
                        self.stdout.write("Publishing course: "
                                          f"{course_sis_id}")
                        result = publish_course_by_sis_id(course_sis_id)

                    if result:
                        modified_courses_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"Successfully {action_taken}ed"
                                               f" {course_sis_id}"))
                        logger.info(f"Successfully {action_taken}ed course "
                                    f"{course_sis_id}")
                    else:
                        failed_count += 1
                        self.stdout.write(
                            self.style.ERROR(f"Failed to {action_taken} "
                                             f"{course_sis_id}"))
                        logger.error(f"Failed to {action_taken} course"
                                     f" {course_sis_id}")

                except Exception as err:
                    failed_count += 1
                    error_msg = f"Error {action_taken}ing course "
                    error_msg += f"{course_sis_id}: {err}"
                    self.stdout.write(self.style.ERROR(f"{error_msg}"))
                    logger.error(error_msg)

            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Dry run complete. {courses.count()} courses would "
                        f"be {'unpublished' if unpublish else 'published'}"))
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{'Unpublish' if unpublish else 'Publish'} operation "
                        "complete. "
                        f"Success: {modified_courses_count}, "
                        f"Failed: {failed_count}"))

        except TrainingCourse.DoesNotExist:
            error_msg = (f"Training course with blueprint SIS ID "
                         f"{training_course_blueprint_sis_id} not found")
            self.stdout.write(self.style.ERROR(error_msg))
            logger.error(error_msg)
            raise CommandError(error_msg)

        except Exception as err:
            error_msg = f"Unexpected error: {err}"
            self.stdout.write(self.style.ERROR(error_msg))
            logger.error(error_msg)
            raise CommandError(error_msg)
