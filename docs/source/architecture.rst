.. _architecture:

Architecture
============

This document describes the overall architecture and design of the Nopayloaddb system.

System Overview
---------------

Nopayloaddb is implemented as a Django REST API that provides a conditions database service for High Energy Physics (HEP) experiments. The system is designed to handle time-dependent calibration and configuration data (payloads) with proper versioning and validity intervals.

Core Components
---------------

Django Application Structure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The application follows standard Django patterns:

- **Main Project**: ``nopayloaddb/`` - Contains settings, URL routing, and WSGI configuration
- **Core App**: ``cdb_rest/`` - Contains all business logic, models, views, and API endpoints
- **Database Router**: ``nopayloaddb.db_router`` - Handles read/write database splitting
- **Middleware**: ``nopayloaddb.middleware`` - Custom request processing

Database Architecture
~~~~~~~~~~~~~~~~~~~~~~

**Multi-Database Setup**

The system supports a read/write splitting architecture:

- **Write Database (default)**: Handles all write operations (CREATE, UPDATE, DELETE)
- **Read Replicas**: ``read_db_1``, ``read_db_2`` - Can handle read operations for improved performance
- **Database Router**: Routes operations to appropriate databases based on operation type

ORM-based operations route to the ``default`` database. The main ``/payloadiovs/`` query
endpoint distributes its raw SQL reads randomly across the configured ``read_db_*``
replicas (falling back to ``default`` when none are configured).

**Schema Design**

The database schema consists of five main tables:

.. code-block:: sql

   GlobalTagStatus -> GlobalTag -> PayloadList -> PayloadIOV
                           |           |
                           v           v
                    PayloadType -------'

Key relationships:

- **GlobalTag** belongs to a **GlobalTagStatus**
- **PayloadList** belongs to a **GlobalTag** and **PayloadType**
- **PayloadIOV** belongs to a **PayloadList**

Data Model
----------

Core Entities
~~~~~~~~~~~~~~

**GlobalTag**
  Named collection of payload versions representing a consistent set of conditions for a specific processing campaign or data-taking period.

**PayloadType** 
  Categorizes payloads by their data type (e.g., 'BeamSpot', 'SiPixelQuality', 'CEMC_Thresh').

**PayloadList**
  Links a GlobalTag to a PayloadType, serving as a container for related payload versions.

**PayloadIOV**
  Individual payload with its Interval of Validity (IOV), containing:

  - Payload URL (reference to actual data file)
  - IOV range (major_iov, minor_iov, major_iov_end, minor_iov_end)
  - Metadata (checksum, size, and an ``extra`` free-form field exposed as ``revision`` in queries)

Validity Model
~~~~~~~~~~~~~~~

**Interval of Validity (IOV)**

Each payload has a validity range defined by:

- ``major_iov``, ``minor_iov`` - Start of validity range
- ``major_iov_end``, ``minor_iov_end`` - End of validity range
- ``comb_iov`` - Combined IOV for efficient indexing

The system supports querying for the appropriate payload based on a specific time point or run number.

**IOV Modes**

The ``CDB_IOV_MODE`` environment variable (``continuous`` by default, or ``discrete``)
selects the boundary semantics used when validating and attaching IOVs. In continuous mode
an IOV's end must be strictly greater than its start; in discrete mode equal boundaries are
allowed and neighboring IOVs are trimmed with a one-unit offset. The strategies live in
``cdb_rest/iov_comparisons.py``.

API Design
-----------

RESTful Architecture
~~~~~~~~~~~~~~~~~~~~~

The API follows REST principles:

- **Resources**: GlobalTags, PayloadTypes, PayloadLists, PayloadIOVs
- **HTTP Methods**: GET (read), POST (create), PUT (update), DELETE (remove)
- **JSON Format**: All data exchange uses JSON
- **Stateless**: Each request contains all necessary information

Query Optimization
~~~~~~~~~~~~~~~~~~~

The system provides multiple query endpoints optimized for different use cases:

- **SQL-based queries**: Direct SQL for complex IOV lookups
- **ORM-based queries**: Django ORM for simpler operations
- **Bulk operations**: Efficient batch creation of payload IOVs

Authentication & Security
--------------------------

**Authentication**
  Configured via the ``CDB_AUTH_CLASS`` environment variable. Empty by default, which
  allows all requests. When set to ``cdb_rest.authentication.CustomJWTAuthentication``,
  write operations (POST, PUT, PATCH, DELETE) require an HS256 JWT bearer token verified
  against the ``JWT_SECRET`` environment variable; reads remain anonymous.

**Permission Plugins**
  Write endpoints additionally consult a permission plugin selected via
  ``CDB_PERMISSION_PLUGIN_CLASS``:

  - ``DummyPermissionPlugin`` (default) — allows everything
  - ``Belle2PermissionPlugin`` — matches JWT claims (``b2cdb:admin``,
    ``b2cdb:createiov``, ``b2cdb:createpayload``) as regular expressions against the
    target object name

  Custom plugins subclass ``cdb_rest.permissions_plugins.base.BasePermissionPlugin``.

**Production Considerations**
  For production deployment:

  - Set ``CDB_AUTH_CLASS`` to enable JWT authentication for writes
  - Configure HTTPS/TLS
  - Set a secure ``JWT_SECRET``
  - Configure a permission plugin appropriate for your experiment

Deployment Architecture
------------------------

Container-Based Deployment
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Docker Compose (Development)**

.. code-block:: yaml

   services:
     db:        # PostgreSQL database
       image: postgres
     webapp:    # Django application
       build: .

**Production Options**

- **Helm Charts**: Official Kubernetes/OpenShift charts for experiment-specific deployments
  
  - Repository: https://github.com/BNLNPPS/nopayloaddb-charts
  - sPHENIX configuration: ``npdbchart_sphenix/``
  - Belle2 configuration: ``npdbchart_belle2_java/``
  
- **OpenShift/Kubernetes**: Using provided templates or Helm charts
- **Traditional**: WSGI server (Gunicorn) + reverse proxy (Nginx)

Environment Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~

The application uses environment variables for configuration:

- Database connections (separate for write/read)
- Secret keys and security settings
- Logging configuration
- Service endpoints

Scalability Considerations
---------------------------

**Database Scaling**

- Read replica support for query load distribution
- Database connection pooling
- Optimized indexes for IOV queries

**Application Scaling**

- Stateless design enables horizontal scaling
- Container-based deployment supports orchestration
- Separate read/write paths for performance optimization

**Storage Scaling**

- Payload data stored as external files (not in database)
- URLs reference distributed storage systems
- Metadata-only approach reduces database load

Monitoring & Observability
----------------------------

**Logging**

- Django request/response logging
- Database query logging
- Application-specific event logging

**Health Checks**

- Database connectivity checks
- Service readiness endpoints
- Container health monitoring

**Metrics**

- API endpoint performance
- Database connection status
- Query execution times