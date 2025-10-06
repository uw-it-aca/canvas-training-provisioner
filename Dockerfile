ARG DJANGO_CONTAINER_VERSION=2.0.11

FROM us-docker.pkg.dev/uwit-mci-axdd/containers/django-container:${DJANGO_CONTAINER_VERSION} AS app-container

USER root

RUN apt-get update && apt-get install libpq-dev -y

USER acait

ADD --chown=acait:acait . /app/
ADD --chown=acait:acait docker/ /app/project/

RUN /app/bin/pip install -r requirements.txt
RUN /app/bin/pip install psycopg2

FROM us-docker.pkg.dev/uwit-mci-axdd/containers/django-test-container:${DJANGO_CONTAINER_VERSION} AS app-test-container

COPY --from=app-container /app/ /app/
COPY --from=app-container /static/ /static/
