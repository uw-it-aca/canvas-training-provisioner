# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

source "/app/bin/activate"
cd /app

python manage.py collectstatic --noinput

if [ "$ENV"  = "localdev" ]
then
  python manage.py migrate
  python manage.py initialize_db

fi
