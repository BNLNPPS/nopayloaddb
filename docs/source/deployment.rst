.. _deployment:

Deployment Guide
================

This guide covers production deployment of the Nopayloaddb service. In short:

1. Configure the application through environment variables (secrets, authentication, database).
2. Run the published container image, either with the official Helm charts (recommended),
   the OpenShift template shipped with this repository, or plain Docker.
3. Put a TLS-terminating reverse proxy or ingress in front of the service.

Configuration
-------------

All configuration is done through environment variables — there is no need to edit
``nopayloaddb/settings.py``. The full reference table is in
:doc:`installation`; the variables that matter most in production are:

.. code-block:: bash

   # Secret used as the Django SECRET_KEY and to verify JWT tokens (HS256)
   export JWT_SECRET='your-very-secure-secret-key-here'

   # Require JWT bearer tokens for write operations (POST/PUT/PATCH/DELETE);
   # reads remain anonymous
   export CDB_AUTH_CLASS=cdb_rest.authentication.CustomJWTAuthentication

   # Authorize writes. The default DummyPermissionPlugin allows everything;
   # Belle2PermissionPlugin authorizes based on JWT claims.
   export CDB_PERMISSION_PLUGIN_CLASS=cdb_rest.permissions_plugins.belle2.Belle2PermissionPlugin

   # IOV boundary semantics: 'continuous' (default) or 'discrete'
   export CDB_IOV_MODE=continuous

   # Write database
   export POSTGRES_DB_W=nopayloaddb_prod
   export POSTGRES_USER_W=npdb_write
   export POSTGRES_PASSWORD_W='secure-password'
   export POSTGRES_HOST_W=db.example.com
   export POSTGRES_PORT_W=5432

   # Read replicas (used by the /payloadiovs/ query endpoint); repeat with _R2
   export POSTGRES_DB_R1=nopayloaddb_prod
   export POSTGRES_USER_R1=npdb_read
   export POSTGRES_PASSWORD_R1='secure-password'
   export POSTGRES_HOST_R1=db-replica.example.com
   export POSTGRES_PORT_R1=5432

.. warning::
   With the default (empty) ``CDB_AUTH_CLASS``, all requests — including writes — are
   accepted without authentication. Always set it in production.

Container Images
----------------

The repository provides three Dockerfiles:

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - File
     - Purpose
   * - ``Dockerfile``
     - Development image used by ``docker-compose.yml``
   * - ``Dockerfile_prod``
     - Production image (CERN CS9 base); clones a tagged release and runs the app with
       Gunicorn, logging to stdout/stderr
   * - ``Dockerfile_release``
     - Image built by the GitHub release workflow and published to the container registry

Prebuilt images are published to GitHub Container Registry, for example:

.. code-block:: bash

   docker pull ghcr.io/bnlnpps/nopayloaddb:v5.0.0

The container listens on port 8000. For a single-host Docker setup, see the Docker
instructions in :doc:`installation` — the same commands apply, pointing the ``POSTGRES_*``
variables at your production database instead.

Helm Charts (Recommended)
-------------------------

Official Helm charts for Kubernetes and OpenShift are maintained in a separate repository
and include experiment-specific configurations:

**Repository**: https://github.com/BNLNPPS/nopayloaddb-charts

- **sPHENIX**: ``npdbchart_sphenix/``
- **Belle II (Java backend)**: ``npdbchart_belle2_java/``

.. code-block:: bash

   git clone https://github.com/BNLNPPS/nopayloaddb-charts.git
   cd nopayloaddb-charts

   # Provide your configuration
   cp /path/to/your/values_sphenix.yaml npdbchart_sphenix/values.yaml

   # Log in to your cluster and deploy (or upgrade an existing release)
   oc login --token='YOUR_TOKEN'
   oc project your-project-name
   helm upgrade --install sphenix-npdb npdbchart_sphenix/

For Belle II, use ``npdbchart_belle2_java/`` with your ``values_belle2-java.yaml`` in the
same way.

To inspect a running release:

.. code-block:: bash

   helm status <release-name>
   oc get pods
   oc logs deployment/<deployment-name>
   oc describe pod <pod-name>

.. note::
   The charts target OpenShift and use OpenShift-specific resources (``ImageStream``,
   ``Route``). For plain Kubernetes they need small modifications — see
   :doc:`kubernetes_dev` for the details.

OpenShift Template
------------------

For a template-based deployment without Helm, the repository ships
``npdb_openshift_template.yaml``:

.. code-block:: bash

   oc login https://your-openshift-cluster.com
   oc new-project npps
   oc create -f npdb_openshift_template.yaml
   oc new-app --template=npdb

Template parameters (database name, credentials, secret key) can be set with ``-p
NAME=value``. The template's ``SECRET_KEY`` parameter is exposed to the application as
``JWT_SECRET``.

Database Setup
--------------

Create the production database with separate write and read users, matching the
application's read/write splitting:

.. code-block:: psql

   CREATE DATABASE nopayloaddb_prod;

   CREATE USER npdb_write WITH PASSWORD 'secure-write-password';
   CREATE USER npdb_read WITH PASSWORD 'secure-read-password';

   GRANT ALL PRIVILEGES ON DATABASE nopayloaddb_prod TO npdb_write;
   GRANT CONNECT ON DATABASE nopayloaddb_prod TO npdb_read;

   \c nopayloaddb_prod

   GRANT USAGE ON SCHEMA public TO npdb_read;
   GRANT SELECT ON ALL TABLES IN SCHEMA public TO npdb_read;
   GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO npdb_read;
   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO npdb_read;

Then apply the schema once with Django migrations (from any container or host with the
production environment variables set):

.. code-block:: bash

   python manage.py migrate

If you operate PostgreSQL read replicas, point ``POSTGRES_*_R1`` / ``POSTGRES_*_R2`` at
them; the main ``/payloadiovs/`` query endpoint distributes its reads across the configured
replicas. In a single-database setup, simply set the ``_R1``/``_R2`` variables to the same
values as ``_W``.

Reverse Proxy and TLS
---------------------

The application serves plain HTTP on port 8000; run it behind a TLS-terminating reverse
proxy (nginx, Apache, or a cluster ingress/route). Keep in mind:

- Forward the standard proxy headers (``Host``, ``X-Forwarded-For``, ``X-Forwarded-Proto``).
- Allow a generous proxy read timeout: conditions queries against large datasets can take
  longer than typical web defaults (the ``/api/cdb_rest/timeout`` endpoint exists
  specifically to test this).
- Restrict direct access to port 8000 and to PostgreSQL from outside your network.
- The Helm charts already include an nginx front end configured this way.
