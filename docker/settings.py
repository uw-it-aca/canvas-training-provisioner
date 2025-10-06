from .base_settings import *
from google.oauth2 import service_account
import os

INSTALLED_APPS += [
    'training_provisioner.apps.TrainingProvisionerConfig',
]

if os.getenv('ENV', 'localdev') == 'localdev':
    DEBUG = True
    TRAINING_IMPORT_CSV_DEBUG = True
    MEDIA_ROOT = os.getenv('TRAINING_IMPORT_CSV_ROOT', '/app/csv')
else:
    TRAINING_IMPORT_CSV_DEBUG = False
    CSRF_TRUSTED_ORIGINS = ['https://' + os.getenv('CLUSTER_CNAME')]
    STORAGES = {
        'default': {
            'BACKEND': 'storages.backends.gcloud.GoogleCloudStorage',
            'OPTIONS': {
                'project_id': os.getenv('STORAGE_PROJECT_ID', ''),
                'bucket_name': os.getenv('STORAGE_BUCKET_NAME', ''),
                'location': os.path.join(os.getenv('STORAGE_DATA_ROOT', '')),
                'credentials': service_account.Credentials.from_service_account_file(
                    '/gcs/credentials.json'),
            }
        },
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    }

TRAINING_IMPORT_ROOT_ACCOUNT_ID = 'uwtraining'
TRAINING_IMPORT_USERS = 'u_acadev_canvas_training-import-users'
