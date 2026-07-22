.. _api-docs:

=================
API Documentation
=================

Nopayloaddb provides a RESTful API for managing global tags, payload types, payload lists, and payload IOVs. This page documents every endpoint with example requests and responses.

.. contents:: Table of Contents
   :local:
   :depth: 2

Quick Start
===========

**Base URL**

All API endpoints are prefixed with ``/api/cdb_rest/``. For example:

.. tabs::

   .. tab:: Local Development
   
      .. code-block:: text
      
         http://localhost:8000/api/cdb_rest/

   .. tab:: Production
   
      .. code-block:: text
      
         http://nopayloaddb.apps.sdcc.bnl.gov/api/cdb_rest/


**Quick Test**

Verify your installation with this simple command:

.. code-block:: bash

   curl http://localhost:8000/api/cdb_rest/global-tags

**Response Formats**

All API responses use JSON format. Successful responses include appropriate HTTP status codes:

- ``200 OK`` - Successful GET request
- ``201 Created`` - Successful POST request (resource created)
- ``204 No Content`` - Successful DELETE request
- ``400 Bad Request`` - Invalid request data
- ``404 Not Found`` - Resource not found
- ``500 Internal Server Error`` - Server error

Authentication
==============

.. note::
   **Default**: The ``CDB_AUTH_CLASS`` environment variable is empty by default, which allows all requests without authentication. See :doc:`deployment` for production authentication setup.

Authentication is configured via the ``CDB_AUTH_CLASS`` environment variable. When set
(e.g. to ``cdb_rest.authentication.CustomJWTAuthentication``), all **write** operations
(POST, PUT, PATCH, DELETE) require a JWT bearer token. Read operations (GET) always remain
anonymous.

.. code-block:: bash

   export CDB_AUTH_CLASS=cdb_rest.authentication.CustomJWTAuthentication
   export JWT_SECRET=your-secret-key

The bundled ``CustomJWTAuthentication`` class verifies HS256-signed tokens against
``JWT_SECRET``. When authentication is enabled, include the token in write requests:

.. code-block:: bash

   curl -X POST -H "Authorization: Bearer YOUR_JWT_TOKEN" \
        -H "Content-Type: application/json" \
        http://localhost:8000/api/cdb_rest/gt -d '{...}'

**Permission Plugins**

Independently of authentication, write endpoints consult a pluggable permission system
configured via the ``CDB_PERMISSION_PLUGIN_CLASS`` environment variable:

- ``cdb_rest.permissions_plugins.dummy.DummyPermissionPlugin`` (default) — allows all requests
- ``cdb_rest.permissions_plugins.belle2.Belle2PermissionPlugin`` — authorizes based on JWT
  claims (``b2cdb:admin``, ``b2cdb:createiov``, ``b2cdb:createpayload``) whose values are
  regular expressions matched against the target global tag or payload list name


Global Tag Endpoints
====================

Global Tags represent named collections of payload versions for consistent conditions management.

List All Global Tags
~~~~~~~~~~~~~~~~~~~~~

.. http:get:: /api/cdb_rest/global-tags

   Retrieve a list of all global tags in the system.

   **Alias of:** ``GET /api/cdb_rest/globalTags`` (legacy path)

   **Example Request:**

   .. code-block:: bash

      curl http://localhost:8000/api/cdb_rest/global-tags

   **Example Response:**

   .. code-block:: json

      [
        {
          "id": 1,
          "name": "sPHENIX_ExampleGT_24",
          "author": "admin",
          "description": "Example global tag for sPHENIX",
          "status": 1,
          "created": "2022-02-21T15:10:00.000000Z"
        }
      ]

Get Global Tag by Name
~~~~~~~~~~~~~~~~~~~~~~

.. http:get:: /api/cdb_rest/global-tags/(str:name)

   Retrieve detailed information about a specific global tag.

   **Alias of:** ``GET /api/cdb_rest/globalTag/(str:name)`` (legacy path)

   :param name: Global tag name
   :type name: string

   **Example Request:**

   .. code-block:: bash

      curl http://localhost:8000/api/cdb_rest/global-tags/sPHENIX_ExampleGT_24

   **Example Response:**

   .. code-block:: json

      {
        "id": 1,
        "name": "sPHENIX_ExampleGT_24",
        "author": "admin",
        "description": "Example global tag for sPHENIX experiment",
        "status": 1,
        "created": "2022-02-21T15:10:00.000000Z",
        "payload_lists": [
          {
            "id": 210,
            "name": "Beam_210",
            "payload_type": "Beam"
          }
        ]
      }

Create Global Tag
~~~~~~~~~~~~~~~~~

.. http:post:: /api/cdb_rest/gt

   Create a new global tag.

   Requires the ``admin`` role for the global tag name when a
   permission plugin is active.

   :<json string name: Global tag name (required, unique)
   :<json string author: Author/creator name (optional)
   :<json string status: Status **name** (required) — must be an existing GlobalTagStatus, e.g. ``unlocked``

   **Example Request:**

   .. code-block:: bash

      curl -X POST http://localhost:8000/api/cdb_rest/gt \
        -H "Content-Type: application/json" \
        -d '{
          "name": "MyNewGT_v1.0",
          "author": "researcher",
          "status": "unlocked"
        }'

   **Example Response:**

   .. code-block:: json

      {
        "id": 2,
        "name": "MyNewGT_v1.0",
        "author": "researcher",
        "status": "unlocked",
        "created": "2025-01-15T10:30:00.000000Z",
        "updated": "2025-01-15T10:30:00.000000Z"
      }

   If the referenced status does not exist, the endpoint returns
   ``{"detail": "GlobalTagStatus not found."}`` with status ``500``.

Clone Global Tag
~~~~~~~~~~~~~~~~

.. http:post:: /api/cdb_rest/global-tags/(str:source_name)/clone/(str:target_name)

   Create a copy of an existing global tag with all its payload lists.

   **Alias of:** ``POST /api/cdb_rest/cloneGlobalTag/(str:source_name)/(str:target_name)`` (legacy path)

   :param source_name: Name of the global tag to clone
   :param target_name: Name for the new global tag
   :type source_name: string
   :type target_name: string

   **Example Request:**

   .. code-block:: bash

      curl -X POST http://localhost:8000/api/cdb_rest/global-tags/sPHENIX_ExampleGT_24/clone/sPHENIX_ExampleGT_25

Change Global Tag Status
~~~~~~~~~~~~~~~~~~~~~~~~~

.. http:put:: /api/cdb_rest/global-tags/(str:name)/change-status/(str:newStatus)

   Update the status of a global tag

   **Alias of:** ``PUT /api/cdb_rest/gt_change_status/(str:name)/(str:newStatus)`` (legacy path)

   :param name: Global tag name
   :param newStatus: New status **name** — must be an existing GlobalTagStatus
   :type name: string
   :type newStatus: string

   **Example Request:**

   .. code-block:: bash

      curl -X PUT http://localhost:8000/api/cdb_rest/global-tags/MyNewGT_v1.0/change-status/locked

   **Status semantics:**

   - ``unlocked`` — fully mutable; attaching overlapping IOVs splits/trims existing ones
   - ``locked`` — append-only; attaching a conflicting IOV is rejected, deletion of the GT is rejected
   - ``frozen`` — immutable; attaching or deleting payload IOVs and deleting the GT are rejected

Delete Global Tag
~~~~~~~~~~~~~~~~~

.. http:delete:: /api/cdb_rest/global-tags/(str:name)/delete

   Delete a global tag and all associated payload lists.

   **Alias of:** ``DELETE /api/cdb_rest/deleteGlobalTag/(str:name)`` (legacy path)

   :param name: Global tag name
   :type name: string

   **Example Request:**

   .. code-block:: bash

      curl -X DELETE http://localhost:8000/api/cdb_rest/global-tags/MyNewGT_v1.0/delete

   .. warning::
      This operation is irreversible and will delete all associated payload lists!

   .. note::
      Global tags with status ``locked`` or ``frozen`` cannot be deleted.

Global Tag Status Management
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. http:get:: /api/cdb_rest/global-tags/statuses
.. http:post:: /api/cdb_rest/global-tags/statuses

   Manage global tag status definitions.

   **Alias of:** ``GET/POST /api/cdb_rest/gtstatus`` (legacy path)

   **Example Request (GET):**

   .. code-block:: bash

      curl http://localhost:8000/api/cdb_rest/global-tags/statuses

Payload Type Endpoints
======================

Payload Types define categories and structures for different kinds of conditions data.

List Payload Types
~~~~~~~~~~~~~~~~~~

.. http:get:: /api/cdb_rest/payload-types

   Retrieve all payload types.

   **Alias of:** ``GET /api/cdb_rest/pt`` (legacy path)

   **Example Request:**

   .. code-block:: bash

      curl http://localhost:8000/api/cdb_rest/payload-types

   **Example Response:**

   .. code-block:: json

      [
        {
          "id": 1,
          "name": "Beam",
          "description": "Beam parameters and conditions"
        },
        {
          "id": 2,
          "name": "SiPixelQuality",
          "description": "Silicon pixel detector quality flags"
        }
      ]

Create Payload Type
~~~~~~~~~~~~~~~~~~~

.. http:post:: /api/cdb_rest/payload-types

   Create a new payload type.

   **Alias of:** ``POST /api/cdb_rest/pt`` (legacy path)

   :<json string name: Payload type name (required, unique)
   :<json string description: Description of the payload type (optional)

   **Example Request:**

   .. code-block:: bash

      curl -X POST http://localhost:8000/api/cdb_rest/payload-types \
        -H "Content-Type: application/json" \
        -d '{
          "name": "CEMC_Calibration",
          "description": "Electromagnetic calorimeter calibration constants"
        }'

Delete Payload Type
~~~~~~~~~~~~~~~~~~~

.. http:delete:: /api/cdb_rest/payload-types/(str:name)/delete

   Delete a payload type.

   **Alias of:** ``DELETE /api/cdb_rest/deletePayloadType/(str:name)`` (legacy path)

   :param name: Payload type name
   :type name: string

   **Example Request:**

   .. code-block:: bash

      curl -X DELETE http://localhost:8000/api/cdb_rest/payload-types/CEMC_Calibration/delete

Payload List Endpoints
======================

Payload Lists link Global Tags to Payload Types and serve as containers for payload versions.

List Payload Lists
~~~~~~~~~~~~~~~~~~

.. http:get:: /api/cdb_rest/payload-lists

   Retrieve all payload lists.

   **Alias of:** ``GET /api/cdb_rest/pl`` (legacy path)

   **Example Request:**

   .. code-block:: bash

      curl http://localhost:8000/api/cdb_rest/payload-lists

Get Payload Lists for Global Tag
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. http:get:: /api/cdb_rest/global-tags/(str:gt_name)/payload-lists

   Retrieve all payload lists associated with a specific global tag.

   **Alias of:** ``GET /api/cdb_rest/gtPayloadLists/(str:gt_name)`` (legacy path)

   :param gt_name: Global tag name
   :type gt_name: string

   **Example Request:**

   .. code-block:: bash

      curl http://localhost:8000/api/cdb_rest/global-tags/sPHENIX_ExampleGT_24/payload-lists

Create Payload List
~~~~~~~~~~~~~~~~~~~

.. http:post:: /api/cdb_rest/payload-lists

   Create a new payload list. The name is **auto-generated** from the payload type name and
   an internal sequence ID (e.g. ``CEMC_Calibration_42``); the list is created detached
   (``global_tag: null``) and must be attached with ``payload-lists/attach``.

   **Alias of:** ``POST /api/cdb_rest/pl`` (legacy path)

   :<json string payload_type: Payload type **name** (required) — must be an existing PayloadType

   **Example Request:**

   .. code-block:: bash

      curl -X POST http://localhost:8000/api/cdb_rest/payload-lists \
        -H "Content-Type: application/json" \
        -d '{
          "payload_type": "CEMC_Calibration"
        }'

   **Example Response:**

   .. code-block:: json

      {
        "id": 42,
        "name": "CEMC_Calibration_42",
        "global_tag": null,
        "payload_type": "CEMC_Calibration",
        "created": "2026-01-15T10:30:00.000000Z"
      }

Get Payload List by Name
~~~~~~~~~~~~~~~~~~~~~~~~

.. http:get:: /api/cdb_rest/payload-lists/by-name/(str:name)

   Retrieve a payload list's metadata by name, including the number of attached payload
   IOVs (``iov_count``). Nested IOVs are not included. This endpoint has no legacy path.

   :param name: Payload list name
   :type name: string

   **Example Request:**

   .. code-block:: bash

      curl http://localhost:8000/api/cdb_rest/payload-lists/by-name/Beam_210

   **Example Response:**

   .. code-block:: json

      {
        "id": 210,
        "name": "Beam_210",
        "global_tag": "sPHENIX_ExampleGT_24",
        "payload_type": "Beam",
        "iov_count": 12,
        "created": "2022-02-21T15:10:00.000000Z"
      }

Attach Payload List to Global Tag
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. http:put:: /api/cdb_rest/payload-lists/attach

   Attach an existing payload list to a global tag. If the global tag already has a payload
   list of the same payload type, that list is detached first. Rejected if the global tag is
   ``frozen``, or if it is ``locked`` and a list of the same type is already attached.

   **Alias of:** ``PUT /api/cdb_rest/pl_attach`` (legacy path)

   :<json string global_tag: Global tag name (required)
   :<json string payload_list: Payload list name (required)

   **Example Request:**

   .. code-block:: bash

      curl -X PUT http://localhost:8000/api/cdb_rest/payload-lists/attach \
        -H "Content-Type: application/json" \
        -d '{
          "global_tag": "sPHENIX_ExampleGT_24",
          "payload_list": "CEMC_Calibration_42"
        }'

Delete Payload List
~~~~~~~~~~~~~~~~~~~

.. http:delete:: /api/cdb_rest/payload-lists/(str:name)/delete

   Delete a payload list and all associated payload IOVs.

   **Alias of:** ``DELETE /api/cdb_rest/deletePayloadList/(str:name)`` (legacy path)

   :param name: Payload list name
   :type name: string

   **Example Request:**

   .. code-block:: bash

      curl -X DELETE http://localhost:8000/api/cdb_rest/payload-lists/CEMC_Calibration_v1.0/delete

Payload IOV Endpoints
=====================

Payload IOVs (Intervals of Validity) represent individual conditions data entries with their validity ranges.

Main Payload Query Endpoint
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. http:get:: /api/cdb_rest/payload-iovs/query/

   **Primary endpoint** for querying payload IOVs. For each payload list attached to the
   global tag, it returns the latest payload IOV whose start is at or before the requested
   IOV point. The query runs as raw SQL for performance and is distributed randomly across
   the configured read replica databases.

   **Alias of:** ``GET /api/cdb_rest/payloadiovs/`` (legacy path)

   :query gtName: Global tag name (required)
   :query majorIOV: Major IOV value (required)
   :query minorIOV: Minor IOV value (required)
   :query shape: Set to ``dict`` to receive a list of JSON objects instead of positional rows (optional)

   **Example Request:**

   .. code-block:: bash

      # Default (positional rows)
      curl 'http://localhost:8000/api/cdb_rest/payload-iovs/query/?gtName=sPHENIX_ExampleGT_24&majorIOV=0&minorIOV=999999'

      # Dictionary-shaped response
      curl 'http://localhost:8000/api/cdb_rest/payload-iovs/query/?gtName=sPHENIX_ExampleGT_24&majorIOV=0&minorIOV=999999&shape=dict'

   **Example Response (default):**

   Each row contains, in order: payload type name, payload URL, checksum, size, major IOV,
   minor IOV, major IOV end, minor IOV end, and revision (from the payload's ``extra`` field):

   .. code-block:: json

      [
        ["Beam", "D0DXMagnets.dat", "e99a18c428cb38d5f260853678922e03", 1024,
         0, 999999, 9223372036854775807, 9223372036854775807, null]
      ]

   **Example Response (shape=dict):**

   .. code-block:: json

      [
        {
          "payload_type_name": "Beam",
          "payload_url": "D0DXMagnets.dat",
          "checksum": "e99a18c428cb38d5f260853678922e03",
          "size": 1024,
          "major_iov": 0,
          "minor_iov": 999999,
          "major_iov_end": 9223372036854775807,
          "minor_iov_end": 9223372036854775807,
          "revision": null
        }
      ]

   .. note::
      The underlying SQL query is selected by the ``CDB_PAYLOAD_IOVS_QUERY`` setting in
      ``nopayloaddb/settings.py``. The current default, ``get_payload_iovs_with_extra``,
      includes the ``revision`` column; the plain ``get_payload_iovs`` query omits it.

Create Payload IOV
~~~~~~~~~~~~~~~~~~

.. http:post:: /api/cdb_rest/payload-iovs

   Create a single payload IOV. The IOV is created **detached** — associate it with a
   payload list afterwards using ``payload-iovs/attach``. If the end values are omitted they
   default to ``sys.maxsize`` (open-ended IOV). A combined IOV
   (``comb_iov = major_iov + minor_iov / 10^19``) is computed automatically.

   **Alias of:** ``POST /api/cdb_rest/piov`` (legacy path)

   :<json string payload_url: URL/path to payload file (required)
   :<json string checksum: File checksum (required)
   :<json int size: File size in bytes (optional)
   :<json int major_iov: Major IOV start (required)
   :<json int minor_iov: Minor IOV start (required)
   :<json int major_iov_end: Major IOV end (optional, defaults to ``sys.maxsize``)
   :<json int minor_iov_end: Minor IOV end (optional, defaults to ``sys.maxsize``)

   **IOV range validation** depends on the ``CDB_IOV_MODE`` setting (see :ref:`iov-modes`):

   - ``continuous`` (default): the end IOV must be strictly greater than the start IOV
   - ``discrete``: the end IOV may be equal to the start IOV (adjacent intervals)

   An invalid range returns ``{"detail": "... PayloadIOV ending IOVs should be greater or
   equal than starting. ..."}`` with status ``500``.

   **Example Request:**

   .. code-block:: bash

      curl -X POST http://localhost:8000/api/cdb_rest/payload-iovs \
        -H "Content-Type: application/json" \
        -d '{
          "payload_url": "calibration_data_v1.2.root",
          "checksum": "sha256:abcd1234ef567890...",
          "size": 2048000,
          "major_iov": 0,
          "minor_iov": 1000,
          "major_iov_end": 0,
          "minor_iov_end": 2000
        }'

   **Example Response:**

   .. code-block:: json

      {
        "id": 1,
        "payload_url": "calibration_data_v1.2.root",
        "checksum": "sha256:abcd1234ef567890...",
        "major_iov": 0,
        "minor_iov": 1000,
        "comb_iov": "0.0000000000000001000",
        "major_iov_end": 0,
        "minor_iov_end": 2000,
        "payload_list": null,
        "inserted": "2026-01-15T10:30:00.000000Z"
      }

Bulk Create Payload IOVs
~~~~~~~~~~~~~~~~~~~~~~~~

.. http:post:: /api/cdb_rest/payload-iovs/bulk

   Create multiple payload IOVs in a single operation for improved performance. Unlike
   ``payload-iovs``, each entry is attached directly to a payload list (by name), end IOVs
   are always set to ``sys.maxsize`` (open-ended), and individual range validation is skipped.

   Each array element requires ``payload_url``, ``major_iov``, ``minor_iov`` and
   ``payload_list`` (payload list **name**).

   **Alias of:** ``POST /api/cdb_rest/bulk_piov`` (legacy path)

   **Example Request:**

   .. code-block:: bash

      curl -X POST http://localhost:8000/api/cdb_rest/payload-iovs/bulk \
        -H "Content-Type: application/json" \
        -d '[
          {
            "payload_url": "data_run1000.root",
            "major_iov": 0,
            "minor_iov": 1000,
            "payload_list": "Beam_210"
          },
          {
            "payload_url": "data_run1500.root",
            "major_iov": 0,
            "minor_iov": 1500,
            "payload_list": "Beam_210"
          }
        ]'

Attach Payload IOV to List
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. http:put:: /api/cdb_rest/payload-iovs/attach

   Attach an existing payload IOV to a payload list, resolving overlaps with the IOVs
   already in the list:

   - If the owning global tag is ``unlocked``, existing IOVs are split or trimmed to
     accommodate the new one (fully covered IOVs are detached from the list).
   - If the global tag is ``locked``, the list is append-only: a conflicting IOV is rejected
     with ``{"detail": "GT is LOCKED. ..."}`` and status ``500``. As a special case, a new
     open-ended IOV starting after the last existing open-ended IOV is accepted (Online GT
     workflow).
   - If the global tag is ``frozen``, the request is rejected.

   Overlap comparisons honor the configured ``CDB_IOV_MODE`` (see :ref:`iov-modes`).

   **Alias of:** ``PUT /api/cdb_rest/piov_attach`` (legacy path)

   :<json string payload_list: Payload list name (required)
   :<json int piov_id: Payload IOV ID (required)

   **Example Request:**

   .. code-block:: bash

      curl -X PUT http://localhost:8000/api/cdb_rest/payload-iovs/attach \
        -H "Content-Type: application/json" \
        -d '{
          "payload_list": "Beam_210",
          "piov_id": 1
        }'

Delete Payload IOV
~~~~~~~~~~~~~~~~~~

.. http:delete:: /api/cdb_rest/payload-iovs/(str:gtName)/(str:payloadType)/(int:majorIOV)/(int:minorIOV)/delete

   Delete a specific payload IOV.

   **Alias of:** ``DELETE /api/cdb_rest/deletePayloadIOV/(str:gtName)/(str:payloadType)/(int:majorIOV)/(int:minorIOV)`` (legacy path)

   :param gtName: Global tag name
   :param payloadType: Payload type name
   :param majorIOV: Major IOV value
   :param minorIOV: Minor IOV value

.. http:delete:: /api/cdb_rest/payload-iovs/(str:gtName)/(str:payloadType)/(int:majorIOV)/(int:minorIOV)/(int:majorIOVEnd)/(int:minorIOVEnd)/delete

   Delete payload IOVs in a range.

   **Alias of:** ``DELETE /api/cdb_rest/deletePayloadIOV/(str:gtName)/(str:payloadType)/(int:majorIOV)/(int:minorIOV)/(int:majorIOVEnd)/(int:minorIOVEnd)`` (legacy path)

   **Example Request:**

   .. code-block:: bash

      # Delete specific IOV
      curl -X DELETE http://localhost:8000/api/cdb_rest/payload-iovs/sPHENIX_ExampleGT_24/Beam/0/1000/delete

      # Delete range of IOVs
      curl -X DELETE http://localhost:8000/api/cdb_rest/payload-iovs/sPHENIX_ExampleGT_24/Beam/0/1000/0/2000/delete

.. _iov-modes:

IOV Modes
=========

The ``CDB_IOV_MODE`` environment variable selects how IOV boundaries are interpreted across
the creation and attachment endpoints. Invalid values cause the application to fail at
startup.

.. list-table::
   :widths: 15 45 40
   :header-rows: 1

   * - Mode
     - Range validation (``payload-iovs``)
     - Overlap handling (``payload-iovs/attach``)
   * - ``continuous`` (default)
     - End IOV must be strictly greater than start IOV
     - Trimmed IOVs end exactly at the new IOV's start
   * - ``discrete``
     - End IOV equal to start IOV is allowed (adjacent intervals)
     - Trimmed IOVs end one unit before the new IOV's start

Settings Endpoint
=================

.. http:get:: /api/cdb_rest/settings/(str:name)/

   Read-only access to the server's ``CDB_*`` configuration values (all environment
   variables prefixed with ``CDB_``).

   **Alias of:** ``GET /api/cdb_rest/user_settings/(str:name)/`` (legacy path)

   :param name: Setting name, e.g. ``CDB_IOV_MODE``
   :type name: string

   **Example Request:**

   .. code-block:: bash

      curl http://localhost:8000/api/cdb_rest/settings/CDB_IOV_MODE/

   **Example Response:**

   .. code-block:: json

      {"CDB_IOV_MODE": "continuous"}

   Unknown names return ``404`` with ``{"detail": "Setting 'NAME' not found."}``.

Utility Endpoints
=================

Test and Utility Functions
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. http:get:: /api/cdb_rest/timeout

   Test endpoint that simulates a long-running request (sleeps for 30 minutes before
   responding). Useful for validating proxy/gateway timeout configuration.

   **Example Request:**

   .. code-block:: bash

      curl http://localhost:8000/api/cdb_rest/timeout

Common Query Patterns
=====================

Here are some common query patterns and use cases:

Get All Conditions for a Run
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Get all conditions for run 12345
   curl 'http://localhost:8000/api/cdb_rest/payload-iovs/query/?gtName=Production_GT_v2.1&majorIOV=0&minorIOV=12345'

List All Available Global Tags
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # See what global tags are available
   curl http://localhost:8000/api/cdb_rest/global-tags | jq '.[].name'

Error Handling
==============

The API provides detailed error messages to help with debugging:

Common HTTP Status Codes
~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 10 20 70
   :header-rows: 1

   * - Code
     - Status
     - Description
   * - 200
     - OK
     - Successful GET request
   * - 201
     - Created
     - Resource created successfully  
   * - 204
     - No Content
     - Successful DELETE request
   * - 400
     - Bad Request
     - Invalid request data or missing required fields
   * - 404
     - Not Found
     - Resource not found (global tag, payload type, etc.)
   * - 409
     - Conflict
     - Resource already exists (duplicate names)
   * - 500
     - Internal Server Error
     - Server error (check logs)

Error Response Format
~~~~~~~~~~~~~~~~~~~~~

Error responses use a single ``detail`` field:

.. code-block:: json

   {
     "detail": "GlobalTag NonExistentGT doesn't exist"
   }

.. note::
   Most business-logic errors (missing resources, immutable global tags, IOV conflicts) are
   currently returned with status ``500`` rather than ``404``/``409``.

Validation Errors
~~~~~~~~~~~~~~~~~

Field validation errors provide specific field-level feedback:

.. code-block:: json

   {
     "name": ["This field is required."],
     "major_iov": ["Ensure this value is greater than or equal to 0."]
   }

Performance Tips
================

Query Optimization
~~~~~~~~~~~~~~~~~~

1. **Batch Operations**: Use bulk endpoints for multiple operations
2. **Appropriate IOV Ranges**: Use precise IOV ranges to limit result sets
3. **Caching**: Cache frequently accessed data on the client side

Database Considerations
~~~~~~~~~~~~~~~~~~~~~~~

- The main ``/payload-iovs/query/`` endpoint is optimized for complex queries
- Bulk operations are significantly faster than individual requests
- Consider using read replicas for high-load query scenarios