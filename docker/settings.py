from .base_settings import *
from google.oauth2 import service_account
import os

INSTALLED_APPS += [
    'training_provisioner.apps.TrainingProvisionerConfig',
]

UW_CANVAS_ROOT_ACCOUNT = os.getenv('UW_CANVAS_ROOT_ACCOUNT')
UW_TRAINING_ROOT_ACCOUNT = os.getenv('UW_TRAINING_ROOT_ACCOUNT')

if os.getenv('ENV', 'localdev') == 'localdev':
    DEBUG = True
    TRAINING_IMPORT_CSV_DEBUG = True
    RESTCLIENTS_DAO_CACHE_CLASS = None
    RESTCLIENTS_CANVAS_ACCOUNT_ID = '123'
    MEDIA_ROOT = os.getenv('TRAINING_IMPORT_CSV_ROOT', '/app/csv')
else:
    TRAINING_IMPORT_CSV_DEBUG = False
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

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache"
    }
}

TRAINING_IMPORT_ROOT_ACCOUNT_ID = 'uwtraining'
TRAINING_IMPORT_USERS = 'u_acadev_canvas_training-import-users'
