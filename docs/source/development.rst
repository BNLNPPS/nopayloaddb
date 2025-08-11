.. _development:

Development Guide
=================

This guide covers development setup, testing, and contribution guidelines for the Nopayloaddb project.

Development Environment
------------------------

Prerequisites
~~~~~~~~~~~~~~

- Python 3.9 or higher
- PostgreSQL 12 or higher
- Git
- Docker and Docker Compose (for containerized development)

Local Development Setup
~~~~~~~~~~~~~~~~~~~~~~~~

**1. Clone and Setup**

.. code-block:: bash

   git clone https://github.com/BNLNPPS/nopayloaddb.git
   cd nopayloaddb
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt

**2. Database Setup**

Create PostgreSQL database and user:

.. code-block:: sql

   CREATE DATABASE nopayloaddb_dev;
   CREATE USER npdb_dev WITH PASSWORD 'dev_password';
   GRANT ALL PRIVILEGES ON DATABASE nopayloaddb_dev TO npdb_dev;

**3. Environment Configuration**

Create a ``.env`` file:

.. code-block:: bash

   export SECRET_KEY='your-development-secret-key-here'
   export DJANGO_LOGPATH='/tmp'
   
   # Database configuration
   export POSTGRES_DB_W=nopayloaddb_dev
   export POSTGRES_USER_W=npdb_dev
   export POSTGRES_PASSWORD_W=dev_password
   export POSTGRES_HOST_W=localhost
   export POSTGRES_PORT_W=5432
   
   # For read replicas (optional in development)
   export POSTGRES_DB_R1=nopayloaddb_dev
   export POSTGRES_USER_R1=npdb_dev
   export POSTGRES_PASSWORD_R1=dev_password
   export POSTGRES_HOST_R1=localhost
   export POSTGRES_PORT_R1=5432

**4. Run Migrations and Start Development Server**

.. code-block:: bash

   source .env
   python manage.py migrate
   python manage.py runserver

Docker Development Setup
~~~~~~~~~~~~~~~~~~~~~~~~~

For a more consistent development environment:

.. code-block:: bash

   git clone https://github.com/BNLNPPS/nopayloaddb.git
   cd nopayloaddb
   
   # Configure .env for Docker
   cat > .env << EOF
   SECRET_KEY='docker-dev-secret-key'
   DJANGO_LOGPATH='/npdb/logs'
   
   POSTGRES_DB_W=nopayloaddb
   POSTGRES_USER_W=npdb
   POSTGRES_PASSWORD_W=password
   POSTGRES_HOST_W=db
   POSTGRES_PORT_W=5432
   EOF
   
   # Start services
   docker-compose up --build

Code Structure
--------------

Project Layout
~~~~~~~~~~~~~~~

.. code-block:: text

   nopayloaddb/
   ├── nopayloaddb/          # Main Django project
   │   ├── __init__.py
   │   ├── settings.py       # Main settings
   │   ├── test_settings.py  # Test-specific settings
   │   ├── urls.py           # Main URL routing
   │   ├── wsgi.py           # WSGI application
   │   ├── db_router.py      # Database routing logic
   │   └── middleware.py     # Custom middleware
   ├── cdb_rest/             # Main application
   │   ├── __init__.py
   │   ├── models.py         # Database models
   │   ├── views.py          # API views
   │   ├── serializers.py    # DRF serializers
   │   ├── urls.py           # API URL routing
   │   ├── queries.py        # Custom queries
   │   ├── authentication.py # Auth logic
   │   └── migrations/       # Database migrations
   ├── docs/                 # Documentation
   ├── requirements.txt      # Python dependencies
   ├── manage.py            # Django management
   ├── Dockerfile           # Container definition
   └── docker-compose.yml   # Development services

Key Components
~~~~~~~~~~~~~~~

**Models (cdb_rest/models.py)**

- ``GlobalTag``: Named collections of payload versions
- ``GlobalTagStatus``: Status management for global tags
- ``PayloadType``: Categorization of payloads
- ``PayloadList``: Links global tags to payload types
- ``PayloadIOV``: Individual payloads with validity intervals

**Views (cdb_rest/views.py)**

- RESTful API endpoints using Django REST Framework
- Custom query views for complex IOV lookups
- Bulk operations for efficient data loading

**Database Router (nopayloaddb/db_router.py)**

- Handles read/write database splitting
- Currently routes all operations to default database
- Ready for read replica scaling

Testing
-------

Test Framework
~~~~~~~~~~~~~~~

The project uses Django's test framework with nose for enhanced testing capabilities.

**Running Tests**

.. code-block:: bash

   # Run all tests
   python manage.py test
   
   # Run specific test module
   python manage.py test cdb_rest.tests.test_models
   
   # Run with coverage
   python manage.py test --with-coverage --cover-package=cdb_rest

**Test Configuration**

Test settings are in ``nopayloaddb/test_settings.py``:

.. code-block:: python

   # Use nose for testing
   TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
   
   # Coverage configuration
   NOSE_ARGS = [
       '--with-coverage',
       '--cover-package=cdb_rest',
   ]

Writing Tests
~~~~~~~~~~~~~~

**Model Tests**

.. code-block:: python

   from django.test import TestCase
   from cdb_rest.models import GlobalTag, GlobalTagStatus
   
   class GlobalTagTestCase(TestCase):
       def setUp(self):
           self.status = GlobalTagStatus.objects.create(
               name='TEST',
               description='Test status'
           )
   
       def test_create_global_tag(self):
           gt = GlobalTag.objects.create(
               name='TestGT',
               author='testuser',
               description='Test global tag',
               status=self.status
           )
           self.assertEqual(gt.name, 'TestGT')
           self.assertEqual(str(gt), 'TestGT')

**API Tests**

.. code-block:: python

   from rest_framework.test import APITestCase
   from rest_framework import status
   
   class GlobalTagAPITestCase(APITestCase):
       def test_create_global_tag(self):
           url = '/api/cdb_rest/gt'
           data = {
               'name': 'TestGT',
               'author': 'testuser',
               'description': 'Test global tag',
               'status': 1
           }
           response = self.client.post(url, data, format='json')
           self.assertEqual(response.status_code, status.HTTP_201_CREATED)

Database Management
-------------------

Migrations
~~~~~~~~~~~

**Creating Migrations**

.. code-block:: bash

   # Create migration for model changes
   python manage.py makemigrations cdb_rest
   
   # Apply migrations
   python manage.py migrate
   
   # Check migration status
   python manage.py showmigrations

**Migration Best Practices**

- Always create migrations for model changes
- Review migration files before applying
- Test migrations on development data
- Use descriptive migration names

**Database Initialization**

.. code-block:: bash

   # Create superuser
   python manage.py createsuperuser
   
   # Load initial data (if fixtures exist)
   python manage.py loaddata initial_data.json

Performance Considerations
---------------------------

Database Optimization
~~~~~~~~~~~~~~~~~~~~~~

**Index Strategy**

The models include optimized indexes:

.. code-block:: python

   class PayloadIOV(models.Model):
       # ... fields ...
       
       class Meta:
           indexes = [
               models.Index('payload_list', F('comb_iov').desc(nulls_last=True), name='covering_idx')
           ]

**Query Optimization**

- Use ``select_related()`` for foreign key relationships
- Use ``prefetch_related()`` for reverse relationships
- Avoid N+1 queries in API endpoints

**Custom Queries**

Complex IOV queries use raw SQL for performance:

.. code-block:: python

   # In cdb_rest/queries.py
   def get_payloads_by_iov(gt_name, major_iov, minor_iov):
       cursor = connection.cursor()
       cursor.execute("""
           SELECT DISTINCT ... FROM PayloadIOV p
           JOIN PayloadList pl ON p.payload_list_id = pl.id
           WHERE pl.global_tag_id = %s AND ...
       """, [gt_name, major_iov, minor_iov])
       return cursor.fetchall()

Code Quality
-------------

Code Style
~~~~~~~~~~~

**PEP 8 Compliance**

- Use 4 spaces for indentation
- Line length limit of 79 characters
- Use descriptive variable names
- Follow Django naming conventions

**Import Organization**

.. code-block:: python

   # Standard library imports
   import os
   import sys
   
   # Third-party imports
   from django.db import models
   from rest_framework import serializers
   
   # Local imports
   from cdb_rest.models import GlobalTag

Documentation
~~~~~~~~~~~~~~

**Docstring Style**

.. code-block:: python

   def get_payloads_by_iov(gt_name, major_iov, minor_iov, payload_type=None):
       """
       Retrieve payloads for a specific global tag and IOV range.
       
       Args:
           gt_name (str): Name of the global tag
           major_iov (int): Major IOV value
           minor_iov (int): Minor IOV value
           payload_type (str, optional): Filter by payload type
       
       Returns:
           QuerySet: Filtered payload IOVs
       """
       pass

**API Documentation**

Use Django REST Framework's built-in documentation features:

.. code-block:: python

   class GlobalTagListCreateAPIView(ListCreateAPIView):
       """
       List all global tags or create a new global tag.
       
       GET: Returns a list of all global tags
       POST: Creates a new global tag
       """
       queryset = GlobalTag.objects.all()
       serializer_class = GlobalTagSerializer

Contributing
-------------

Git Workflow
~~~~~~~~~~~~~

**Branch Strategy**

- ``master``: Main development branch
- ``feature/feature-name``: Feature development
- ``bugfix/bug-description``: Bug fixes
- ``hotfix/urgent-fix``: Production hotfixes

**Commit Messages**

.. code-block:: text

   feat: add bulk payload IOV creation endpoint
   
   - Add new endpoint for bulk creation of payload IOVs
   - Improve performance for large data loads
   - Add validation for bulk operations
   
   Closes #123

**Pull Request Process**

1. Create feature branch from master
2. Make changes with appropriate tests
3. Ensure all tests pass
4. Update documentation if needed
5. Create pull request with description
6. Address code review feedback
7. Merge after approval

Code Review Guidelines
~~~~~~~~~~~~~~~~~~~~~~~

**Review Checklist**

- [ ] Code follows project style guidelines
- [ ] Tests are included and passing
- [ ] Documentation is updated
- [ ] No sensitive information in code
- [ ] Performance impact considered
- [ ] Security implications reviewed

**Common Issues to Check**

- SQL injection vulnerabilities
- Proper error handling
- Resource cleanup (database connections)
- Appropriate HTTP status codes
- Input validation

Development Tools
------------------

Useful Commands
~~~~~~~~~~~~~~~~

**Database Operations**

.. code-block:: bash

   # Reset database
   python manage.py flush
   
   # Dump data
   python manage.py dumpdata cdb_rest --indent=2 > data.json
   
   # Load data
   python manage.py loaddata data.json
   
   # Database shell
   python manage.py dbshell

**Development Server**

.. code-block:: bash

   # Run with debugging
   python manage.py runserver --verbosity=2
   
   # Run on specific port
   python manage.py runserver 0.0.0.0:9000

**Management Commands**

.. code-block:: bash

   # Django shell
   python manage.py shell
   
   # Create superuser
   python manage.py createsuperuser
   
   # Collect static files
   python manage.py collectstatic

IDE Configuration
~~~~~~~~~~~~~~~~~~

**VS Code Settings**

.. code-block:: json

   {
       "python.defaultInterpreterPath": "./venv/bin/python",
       "python.linting.enabled": true,
       "python.linting.pylintEnabled": false,
       "python.linting.flake8Enabled": true,
       "python.formatting.provider": "black",
       "python.testing.pytestEnabled": false,
       "python.testing.unittestEnabled": true,
       "python.testing.unittestArgs": [
           "-v",
           "-s",
           ".",
           "-p",
           "test_*.py"
       ]
   }

**PyCharm Configuration**

- Set Python interpreter to virtual environment
- Configure Django settings module: ``nopayloaddb.settings``
- Enable Django support in project settings
- Configure database connection for database tools

Debugging
----------

Common Issues
~~~~~~~~~~~~~

**Database Connection Issues**

.. code-block:: python

   # Check database connectivity
   from django.db import connection
   cursor = connection.cursor()
   cursor.execute("SELECT 1")
   print(cursor.fetchone())

**Migration Issues**

.. code-block:: bash

   # Check migration status
   python manage.py showmigrations
   
   # Fake migration (if needed)
   python manage.py migrate --fake cdb_rest 0001_initial

**Performance Issues**

.. code-block:: python

   # Enable SQL logging
   import logging
   logging.basicConfig()
   logging.getLogger('django.db.backends').setLevel(logging.DEBUG)

Debug Tools
~~~~~~~~~~~~

**Django Debug Toolbar**

Add to development requirements:

.. code-block:: python

   # In settings.py for development
   if DEBUG:
       INSTALLED_APPS.append('debug_toolbar')
       MIDDLEWARE.append('debug_toolbar.middleware.DebugToolbarMiddleware')
       INTERNAL_IPS = ['127.0.0.1']

**Django Extensions**

Useful for development:

.. code-block:: bash

   pip install django-extensions
   
   # Shell with IPython
   python manage.py shell_plus
   
   # Generate model graph
   python manage.py graph_models -a -g -o models.png