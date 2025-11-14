from .base_settings import *
from google.oauth2 import service_account
import os

STUDENTTRAINING_ADMIN_GROUP='u_acadev_studenttraining_admins'

INSTALLED_APPS += [
    'training_provisioner.apps.TrainingProvisionerConfig',
    'rest_framework.authtoken',
]

CANVAS_ACCOUNT_DOMAIN = os.getenv('CANVAS_ACCOUNT_DOMAIN')
RESTCLIENTS_CANVAS_HOST = ("https://"
                           f"{os.getenv('STUDENTTRAINING_ACCOUNT_DOMAIN')}")

if os.getenv('AUTH', 'NONE') == 'SAML_MOCK':
    MOCK_SAML_ATTRIBUTES = {
        'uwnetid': ['jstaff'],
        'affiliations': ['employee', 'member'],
        'eppn': ['jstaff@washington.edu'],
        'scopedAffiliations': [
            'employee@washington.edu', 'member@washington.edu'],
        'isMemberOf': ['u_test_group', 'u_test_another_group',
                       'u_acadev_studenttraining_admins'],
    }

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
