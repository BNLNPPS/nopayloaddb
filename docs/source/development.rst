.. _development:

Development Guide
=================

This guide covers setting up a development environment, the code layout, testing, and how
to contribute.

Prerequisites
-------------

- Python 3.9 or higher
- PostgreSQL 12 or higher
- Git
- Docker and Docker Compose (optional, for containerized development)

Local Development Setup
-----------------------

**1. Clone and install dependencies**

.. code-block:: bash

   git clone https://github.com/BNLNPPS/nopayloaddb.git
   cd nopayloaddb
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

**2. Create a PostgreSQL database and user**

.. code-block:: sql

   CREATE DATABASE nopayloaddb_dev;
   CREATE USER npdb_dev WITH PASSWORD 'dev_password';
   GRANT ALL PRIVILEGES ON DATABASE nopayloaddb_dev TO npdb_dev;

**3. Configure the environment**

Create a ``.env`` file (see :doc:`installation` for the full variable reference):

.. code-block:: bash

   export JWT_SECRET='your-development-secret-key-here'
   export DJANGO_LOGPATH='/tmp'

   export POSTGRES_DB_W=nopayloaddb_dev
   export POSTGRES_USER_W=npdb_dev
   export POSTGRES_PASSWORD_W=dev_password
   export POSTGRES_HOST_W=localhost
   export POSTGRES_PORT_W=5432

   # Read replicas: point at the same database in development
   export POSTGRES_DB_R1=nopayloaddb_dev
   export POSTGRES_USER_R1=npdb_dev
   export POSTGRES_PASSWORD_R1=dev_password
   export POSTGRES_HOST_R1=localhost
   export POSTGRES_PORT_R1=5432

**4. Migrate and run**

.. code-block:: bash

   source .env
   python manage.py migrate
   python manage.py runserver

The API is now available at http://127.0.0.1:8000/api/cdb_rest/.

Alternative environments
~~~~~~~~~~~~~~~~~~~~~~~~

- **Docker Compose**: ``docker-compose up --build`` starts PostgreSQL and the web app
  together; see the Docker section of :doc:`installation` for the ``.env`` file it expects.
- **Local Kubernetes / OpenShift**: to develop against the full stack (Django + pgbouncer +
  nginx) with the official Helm charts, see :doc:`kubernetes_dev`.

Code Structure
--------------

.. code-block:: text

   nopayloaddb/
   ├── nopayloaddb/          # Main Django project
   │   ├── settings.py       # Main settings (all config via environment variables)
   │   ├── test_settings.py  # Test-specific settings
   │   ├── urls.py           # Main URL routing
   │   ├── wsgi.py           # WSGI application
   │   ├── db_router.py      # Read/write database routing
   │   └── middleware.py     # Custom request middleware
   ├── cdb_rest/             # Main application
   │   ├── models.py         # Database models
   │   ├── views.py          # API views
   │   ├── serializers.py    # DRF serializers
   │   ├── urls.py           # API URL routing
   │   ├── queries.py        # Raw SQL queries for payload IOV lookups
   │   ├── iov_comparisons.py # IOV mode strategies (continuous/discrete)
   │   ├── authentication.py # JWT authentication class
   │   ├── utils.py          # Auth/permission class loaders
   │   ├── permissions_plugins/ # Pluggable write-permission system
   │   │   ├── base.py       # BasePermissionPlugin ABC
   │   │   ├── dummy.py      # Allow-all plugin (default)
   │   │   └── belle2.py     # Belle II JWT-claims-based plugin
   │   └── migrations/       # Database migrations
   ├── docs/                 # This documentation
   ├── requirements.txt      # Python dependencies
   ├── manage.py             # Django management
   ├── Dockerfile            # Development container
   └── docker-compose.yml    # Development services

Key components:

- **Models** (``cdb_rest/models.py``): ``GlobalTag``, ``GlobalTagStatus``, ``PayloadType``,
  ``PayloadList``, ``PayloadIOV`` — see :doc:`cdb_models`.
- **Views** (``cdb_rest/views.py``): DRF class-based views for all endpoints — see
  :doc:`cdb_views` and :doc:`api`.
- **Performance-critical queries** live as raw SQL in ``cdb_rest/queries.py``; the query
  used by ``/payloadiovs/`` is selected by the ``CDB_PAYLOAD_IOVS_QUERY`` setting.
- **Database router** (``nopayloaddb/db_router.py``) implements read/write splitting; the
  ``/payloadiovs/`` endpoint additionally distributes reads across ``read_db_*`` replicas.

Testing
-------

The project uses Django's test framework with django-nose for coverage reporting
(configured in ``nopayloaddb/test_settings.py`` via ``NOSE_ARGS``).

.. code-block:: bash

   # Run all tests
   python manage.py test

   # Run a specific test module
   python manage.py test cdb_rest.tests.test_models

   # Run with coverage
   python manage.py test --with-coverage --cover-package=cdb_rest

Example API test — note that ``status`` is the **name** of an existing
``GlobalTagStatus`` and the create endpoint responds with ``200``:

.. code-block:: python

   from rest_framework.test import APITestCase
   from cdb_rest.models import GlobalTagStatus

   class GlobalTagAPITestCase(APITestCase):
       def setUp(self):
           GlobalTagStatus.objects.create(name='unlocked')

       def test_create_global_tag(self):
           response = self.client.post('/api/cdb_rest/gt', {
               'name': 'TestGT',
               'author': 'testuser',
               'status': 'unlocked',
           }, format='json')
           self.assertEqual(response.status_code, 200)

Database Migrations
-------------------

.. code-block:: bash

   python manage.py makemigrations cdb_rest   # create migrations for model changes
   python manage.py migrate                   # apply them
   python manage.py showmigrations            # check status

Always create and review migrations for model changes, and test them against development
data before merging.

Useful Commands
---------------

.. code-block:: bash

   python manage.py shell                     # Django shell
   python manage.py dbshell                   # database shell
   python manage.py flush                     # reset database contents
   python manage.py dumpdata cdb_rest --indent=2 > data.json
   python manage.py loaddata data.json
   python manage.py runserver 0.0.0.0:9000    # serve on a specific address/port

To trace SQL while debugging performance:

.. code-block:: python

   import logging
   logging.basicConfig()
   logging.getLogger('django.db.backends').setLevel(logging.DEBUG)

Contributing
------------

1. Create a feature branch from ``master``.
2. Make your changes, following the surrounding code style (PEP 8, Django conventions),
   with tests where appropriate.
3. Ensure the test suite passes and update the documentation if behavior changed.
4. Open a pull request describing the change and address review feedback.

Please report bugs and feature requests on
`GitHub Issues <https://github.com/BNLNPPS/nopayloaddb/issues>`_.
