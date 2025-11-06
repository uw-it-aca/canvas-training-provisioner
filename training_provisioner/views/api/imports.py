# Copyright 2025 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from training_provisioner.models import Import
from training_provisioner.views.api import StudentTrainingAPI
from logging import getLogger

logger = getLogger(__name__)


class ImportInvalidException(Exception):
    pass


class ImportView(StudentTrainingAPI):
    """ Retrieves an Import model.
        GET returns 200 with Import details.
        DELETE returns 200.
    """
    def get(self, request, *args, **kwargs):
        import_id = kwargs['import_id']
        try:
            imp = Import.objects.get(id=import_id)
            return self.json_response(imp.json_data())
        except Import.DoesNotExist:
            return self.error_response(
                404, "Import {} not found".format(import_id))
        except ImportInvalidException as err:
            return self.error_response(400, err)

    def delete(self, request, *args, **kwargs):
        import_id = kwargs['import_id']
        try:
            imp = Import.objects.get(id=import_id)

            logger.info(
                'imports ({}): DELETE: type: {}, queue_id: {}, '
                'post_status: {}, canvas_state: {}'.format(
                    request.user, imp.csv_type, imp.pk, imp.post_status,
                    imp.canvas_state))

            imp.delete()

            return self.json_response()

        except Import.DoesNotExist:
            return self.error_response(
                404, "Import {} not found".format(import_id))
        except ImportInvalidException as err:
            return self.error_response(400, err)


class ImportListView(StudentTrainingAPI):
    """ Retrieves a list of Imports at /api/v1/imports/?<criteria[&criteria]>.
        GET returns 200 with Import details.
    """
    def get(self, request, *args, **kwargs):
        json_rep = {
            'imports': []
        }

        try:
            import_list = Import.objects.all().order_by('added_date')
        except ImportInvalidException as err:
            return self.error_response(400, err)

        for imp in import_list:
            json_rep['imports'].append(imp.json_data())

        return self.json_response(json_rep)
