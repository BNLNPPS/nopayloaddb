.. _install:

Installation
============

This guide provides comprehensive instructions for setting up the Nopayloaddb project. Choose the installation method that best fits your needs:

- **Quick Start with Docker** (Recommended): Get up and running in minutes
- **Manual Installation**: For development or custom setups
- **Production Deployment**: For production environments

.. note::
   **TL;DR - Quick Start**: If you just want to try Nopayloaddb quickly, jump to :ref:`docker-quickstart`.

.. _docker-quickstart:

Quick Start with Docker (Recommended)
--------------------------------------

The fastest way to get Nopayloaddb running:

**Prerequisites:**
- Docker and Docker Compose installed on your system

**Steps:**

1. **Clone and Setup:**
   
   .. code-block:: bash

      git clone https://github.com/BNLNPPS/nopayloaddb.git
      cd nopayloaddb

2. **Create Environment File:**
   
   .. code-block:: bash

      cat > .env << 'EOF'
      # Basic configuration for development
      JWT_SECRET='development-secret-key-change-in-production'
      DJANGO_LOGPATH='/tmp'
      
      # Database configuration
      POSTGRES_DB_W=nopayloaddb
      POSTGRES_USER_W=npdb
      POSTGRES_PASSWORD_W=password
      POSTGRES_HOST_W=db
      POSTGRES_PORT_W=5432
      EOF

3. **Start the Application:**
   
   .. code-block:: bash

      docker-compose up --build

4. **Access the Application:**

   **API Endpoints:**
   - API Documentation: http://localhost:8000/api/cdb_rest/
   - Sample API call: 
     
     .. code-block:: bash
     
        curl http://localhost:8000/api/cdb_rest/gt

That's it! You now have Nopayloaddb running with a PostgreSQL database.

**Managing the environment**

.. code-block:: bash

   docker-compose logs -f webapp                          # follow application logs
   docker-compose exec webapp python manage.py shell      # Django shell in the container
   docker-compose exec webapp python manage.py migrate    # run migrations if needed
   docker-compose down                                    # stop services
   rm -fr db/data                                         # reset the database (removes all data)

.. _manual-installation:

Manual Installation
-------------------

For developers who want more control or need to customize the setup.

.. _prerequisites:

Prerequisites
~~~~~~~~~~~~~

System Requirements
^^^^^^^^^^^^^^^^^^^

**Required Software:**

- **Python 3.8+** (Python 3.9+ recommended)
- **PostgreSQL 12+** (13+ recommended for better performance)
- **Git** (for cloning the repository)

**System Dependencies:**

The following system packages are required for PostgreSQL connectivity:

.. tabs::

   .. tab:: Ubuntu/Debian
   
      .. code-block:: bash
      
         sudo apt-get update
         sudo apt-get install -y \
             python3-dev \
             libpq-dev \
             postgresql \
             postgresql-contrib \
             git

   .. tab:: CentOS/RHEL/Fedora
   
      .. code-block:: bash
      
         # CentOS/RHEL
         sudo yum install -y \
             python3-devel \
             postgresql-devel \
             postgresql-server \
             postgresql-contrib \
             git
             
         # Fedora
         sudo dnf install -y \
             python3-devel \
             postgresql-devel \
             postgresql-server \
             postgresql-contrib \
             git

   .. tab:: macOS
   
      .. code-block:: bash
      
         # Using Homebrew
         brew install postgresql git
         
         # Start PostgreSQL service
         brew services start postgresql

   .. tab:: Windows
   
      1. Install PostgreSQL from https://www.postgresql.org/download/windows/
      2. Install Git from https://git-scm.com/download/win
      3. Install Python from https://www.python.org/downloads/

Installation Steps
~~~~~~~~~~~~~~~~~~

1. **Clone the Repository**
   
   .. code-block:: bash

      git clone https://github.com/BNLNPPS/nopayloaddb.git
      cd nopayloaddb

2. **Create Virtual Environment**
   
   .. code-block:: bash

      python3 -m venv venv
      
      # Activate virtual environment
      # Linux/macOS:
      source venv/bin/activate
      
      # Windows:
      # venv\Scripts\activate

   .. tip::
      Always use a virtual environment to avoid conflicts with system packages.

3. **Install Python Dependencies**
   
   .. code-block:: bash

      pip install --upgrade pip
      pip install -r requirements.txt

4. **Database Setup**

   **Create PostgreSQL Database and User:**

   .. code-block:: bash

      # Connect to PostgreSQL as superuser
      sudo -u postgres psql

   .. code-block:: psql

      -- Create database
      CREATE DATABASE nopayloaddb_dev;
      
      -- Create user with password
      CREATE USER npdb_dev WITH PASSWORD 'secure_dev_password';
      
      -- Grant privileges
      GRANT ALL PRIVILEGES ON DATABASE nopayloaddb_dev TO npdb_dev;
      
      -- Exit PostgreSQL
      \q

   .. note::
      For production, use separate read/write users. See :ref:`production-database-setup`.

5. **Environment Configuration**

   Create a `.env` file in the project root:

   .. code-block:: bash

      cat > .env << 'EOF'
      # Security (used as the Django SECRET_KEY and to verify JWT tokens)
      JWT_SECRET='your-very-secure-secret-key-here'
      
      # Logging
      DJANGO_LOGPATH='/tmp'
      
      # Write Database (Primary)
      POSTGRES_DB_W=nopayloaddb_dev
      POSTGRES_USER_W=npdb_dev
      POSTGRES_PASSWORD_W=secure_dev_password
      POSTGRES_HOST_W=localhost
      POSTGRES_PORT_W=5432
      
      # Read Replicas (Optional - can use same values as write DB for development)
      POSTGRES_DB_R1=nopayloaddb_dev
      POSTGRES_USER_R1=npdb_dev
      POSTGRES_PASSWORD_R1=secure_dev_password
      POSTGRES_HOST_R1=localhost
      POSTGRES_PORT_R1=5432
      
      POSTGRES_DB_R2=nopayloaddb_dev
      POSTGRES_USER_R2=npdb_dev
      POSTGRES_PASSWORD_R2=secure_dev_password
      POSTGRES_HOST_R2=localhost
      POSTGRES_PORT_R2=5432
      EOF

   .. warning::
      **Generate a secure JWT_SECRET**: You can generate one using:
      
      .. code-block:: bash
      
         python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

6. **Apply Database Migrations**

   .. code-block:: bash

      # Load environment variables
      source .env
      
      # Apply migrations
      python manage.py migrate

7. **Create Superuser (Optional)**

   .. code-block:: bash

      python manage.py createsuperuser

8. **Run Development Server**

   .. code-block:: bash

      python manage.py runserver

   Access the application at http://127.0.0.1:8000/

Environment Variables Reference
-------------------------------

Complete reference for all supported environment variables:

Core Settings
~~~~~~~~~~~~~

.. list-table::
   :widths: 25 50 25
   :header-rows: 1

   * - Variable
     - Description
     - Default
   * - ``JWT_SECRET``
     - Django secret key, also used to verify JWT tokens (**required**)
     - ``'changetosomething'`` (insecure)
   * - ``DJANGO_LOGPATH``
     - Path for Django log files
     - ``'/var/log'``
   * - ``CDB_AUTH_CLASS``
     - Authentication class for write operations, e.g. ``cdb_rest.authentication.CustomJWTAuthentication``. Empty allows all requests.
     - *(empty)*
   * - ``CDB_PERMISSION_PLUGIN_CLASS``
     - Permission plugin class for write operations
     - ``cdb_rest.permissions_plugins.dummy.DummyPermissionPlugin``
   * - ``CDB_IOV_MODE``
     - IOV mode: ``continuous`` or ``discrete``
     - ``continuous``

Database Configuration
~~~~~~~~~~~~~~~~~~~~~~

**Write Database (Primary):**

.. list-table::
   :widths: 25 50 25
   :header-rows: 1

   * - Variable
     - Description
     - Default
   * - ``POSTGRES_DB_W``
     - Write database name
     - ``'dbname'``
   * - ``POSTGRES_USER_W``
     - Write database user
     - ``'login'``
   * - ``POSTGRES_PASSWORD_W``
     - Write database password
     - ``'password'``
   * - ``POSTGRES_HOST_W``
     - Write database host
     - ``'localhost'``
   * - ``POSTGRES_PORT_W``
     - Write database port
     - ``'5432'``

**Read Replicas (Optional):**

Replace ``_W`` with ``_R1`` or ``_R2`` for read replica configuration.

.. _production-database-setup:

Production Deployment
---------------------

Production setup is covered in :doc:`deployment`. In summary:

- Use a secure, randomly generated ``JWT_SECRET`` and enable authentication with
  ``CDB_AUTH_CLASS``.
- Use separate database users for write (``POSTGRES_*_W``) and read (``POSTGRES_*_R1/R2``)
  operations.
- Serve the application behind a TLS-terminating reverse proxy.
- For Kubernetes/OpenShift, use the official Helm charts:
  https://github.com/BNLNPPS/nopayloaddb-charts

Troubleshooting
---------------

Common Issues and Solutions
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Database Connection Errors**

.. code-block:: text

   django.db.utils.OperationalError: could not connect to server

**Solutions:**

1. Verify PostgreSQL is running:
   
   .. code-block:: bash
   
      # Linux/macOS
      sudo systemctl status postgresql
      # or
      brew services list | grep postgresql

2. Check database credentials in your `.env` file
3. Ensure the database exists:
   
   .. code-block:: bash
   
      psql -h localhost -U postgres -l

**Permission Denied on Log Directory**

.. code-block:: text

   PermissionError: [Errno 13] Permission denied: '/var/log/django-hostname.log'

**Solution:**

Set ``DJANGO_LOGPATH`` to a writable directory:

.. code-block:: bash

   export DJANGO_LOGPATH='/tmp'
   # or create logs directory in project
   mkdir -p logs
   export DJANGO_LOGPATH='./logs'

**Module Import Errors**

.. code-block:: text

   ModuleNotFoundError: No module named 'psycopg2'

**Solutions:**

1. Ensure virtual environment is activated
2. Install system dependencies (see :ref:`prerequisites`)
3. Reinstall requirements:
   
   .. code-block:: bash
   
      pip install --upgrade -r requirements.txt

**Docker Issues**

**Port Already in Use:**

.. code-block:: bash

   # Find and stop conflicting process
   sudo lsof -i :8000
   sudo kill <PID>

**Container Build Failures:**

.. code-block:: bash

   # Clean Docker cache and rebuild
   docker system prune -f
   docker-compose build --no-cache

Getting Help
~~~~~~~~~~~~

If you encounter issues not covered here, run ``python manage.py check`` to validate the
configuration, review the Django logs, and check the
`GitHub Issues <https://github.com/BNLNPPS/nopayloaddb/issues>`_. The Docker setup is a
good fallback when the manual installation misbehaves.

Next Steps
----------

After successful installation:

1. **Read the Usage Guide**: See :doc:`usage` for API examples
2. **Development**: See :doc:`development` for development guidelines
3. **Architecture**: Learn about the system in :doc:`architecture`

.. tip::
   **Quick API Test**: Try this command to verify everything is working:
   
   .. code-block:: bash
   
      curl -H "Content-Type: application/json" http://localhost:8000/api/cdb_rest/gt