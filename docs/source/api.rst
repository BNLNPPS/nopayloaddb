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

All API responses use JSON format. Successful write operations (POST, PUT, DELETE)
return ``200 OK`` with a JSON body. Other HTTP status codes indicate errors:

- ``200 OK`` - Successful request, including creates and deletes
- ``400 Bad Request`` - Invalid request data (serializer validation errors)
- ``403 Forbidden`` - Rejected by the configured permission plugin
- ``404 Not Found`` - Resource not found (lookups by ID/name, unknown settings)
- ``500 Internal Server Error`` - Business-logic errors (missing referenced resources, locked/frozen global tags, IOV conflicts) and unhandled server errors

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


.. _browse-mode:

Pagination, Search and Sorting
==============================

The main list endpoints — ``global-tags``, ``payload-types``, ``payload-lists`` and
``payload-iovs`` — return plain, unpaginated JSON arrays by default. Passing a ``page``
query parameter switches them into a paginated *browse mode* with server-side search,
sorting and filtering:

:query page: Page number, 1-based. The presence of this parameter enables browse mode
:query page_size: Items per page, 1–1000 (default ``25``)
:query search: Case-insensitive substring search
:query sort: Sort field (whitelisted per endpoint; unknown values fall back to the default)
:query order: ``asc`` (default) or ``desc``

Additional filters per endpoint:

.. list-table::
   :widths: 25 30 45
   :header-rows: 1

   * - Endpoint
     - Filters
     - Search fields
   * - ``global-tags``
     - ``status``
     - ``name``, ``author``
   * - ``payload-types``
     - —
     - ``name``
   * - ``payload-lists``
     - ``global_tag``, ``payload_type``
     - ``name``, ``global_tag__name``, ``payload_type__name``
   * - ``payload-iovs``
     - ``payload_list``, ``global_tag``, ``payload_type``
     - ``payload_url``, ``payload_list__name``

**Example Request:**

.. code-block:: bash

   curl 'http://localhost:8000/api/cdb_rest/global-tags?page=1&page_size=2&sort=created&order=desc'

**Example Response:**

.. code-block:: json

   {
     "count": 2,
     "page": 1,
     "page_size": 2,
     "total_pages": 1,
     "results": [
       {
         "id": 1,
         "name": "MyNewGT_v1.0",
         "author": "researcher",
         "status": "unlocked",
         "payload_lists_count": 1,
         "payload_iov_count": 2,
         "created": "2026-07-23T00:00:26.714171",
         "updated": "2026-07-23T00:05:32.399958"
       }
     ]
   }

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

   Supports :ref:`browse mode <browse-mode>` via ``?page=``, with a ``status`` filter.

   **Example Response:**

   .. code-block:: json

      [
        {
          "id": 1,
          "name": "sPHENIX_ExampleGT_24",
          "author": "admin",
          "status": "unlocked",
          "payload_lists_count": 1,
          "payload_iov_count": 2,
          "created": "2022-02-21T15:10:00.000000",
          "updated": "2022-02-21T15:10:00.000000"
        }
      ]

   .. note::
      The legacy ``GET /api/cdb_rest/gt`` endpoint also lists all global tags, but
      returns the full nested representation (same shape as *Get Global Tag by Name*)
      for every tag, which can be very large.

Get Global Tag by Name
~~~~~~~~~~~~~~~~~~~~~~

.. http:get:: /api/cdb_rest/global-tags/(str:name)

   Retrieve detailed information about a specific global tag, including all payload
   lists and their payload IOVs fully nested.

   **Alias of:** ``GET /api/cdb_rest/globalTag/(str:name)`` (legacy path)

   :param name: Global tag name
   :type name: string
   :query light: If present (e.g. ``?light=1``), return metadata only — no nested
      payload lists, but ``payload_lists_count`` and ``payload_iov_count`` computed
      in the database (same shape as the list endpoint)

   **Example Request:**

   .. code-block:: bash

      curl http://localhost:8000/api/cdb_rest/global-tags/sPHENIX_ExampleGT_24

   **Example Response:**

   .. code-block:: json

      {
        "id": 1,
        "name": "sPHENIX_ExampleGT_24",
        "author": "admin",
        "status": {
          "id": 1,
          "name": "unlocked",
          "description": null,
          "created": "2022-02-21T15:00:00.000000"
        },
        "payload_lists": [
          {
            "id": 210,
            "name": "Beam_210",
            "global_tag": "sPHENIX_ExampleGT_24",
            "payload_type": "Beam",
            "payload_iov": [
              {
                "id": 1,
                "payload_url": "D0DXMagnets.dat",
                "checksum": "e99a18c428cb38d5f260853678922e03",
                "major_iov": 0,
                "minor_iov": 0,
                "comb_iov": "0.0000000000000000000",
                "major_iov_end": 9223372036854775807,
                "minor_iov_end": 9223372036854775807,
                "payload_list": "Beam_210",
                "inserted": "2022-02-21T15:10:00.000000"
              }
            ],
            "created": "2022-02-21T15:10:00.000000"
          }
        ],
        "created": "2022-02-21T15:10:00.000000",
        "updated": "2022-02-21T15:10:00.000000"
      }

   Unknown names return ``404`` with ``{"detail": "Not found."}``.

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

   **Example Response** (returned with status ``200``):

   .. code-block:: json

      {
        "id": 2,
        "name": "MyNewGT_v1.0",
        "author": "researcher",
        "status": "unlocked",
        "created": "2026-07-23T00:00:26.714171",
        "updated": "2026-07-23T00:00:26.714184"
      }

   If the referenced status does not exist, the request fails with an unhandled
   server error (``500`` with an HTML body, no JSON ``detail``). A duplicate name
   returns ``400`` with ``{"name": ["global tag with this name already exists."]}``.

Clone Global Tag
~~~~~~~~~~~~~~~~

.. http:post:: /api/cdb_rest/global-tags/(str:source_name)/clone/(str:target_name)

   Create a deep copy of an existing global tag with all its payload lists and payload
   IOVs. The clone is always created with status ``unlocked``, and the copied payload
   lists get new auto-generated names (payload type + new sequence ID).

   **Alias of:** ``POST /api/cdb_rest/cloneGlobalTag/(str:source_name)/(str:target_name)`` (legacy path)

   :param source_name: Name of the global tag to clone
   :param target_name: Name for the new global tag
   :type source_name: string
   :type target_name: string

   **Example Request:**

   .. code-block:: bash

      curl -X POST http://localhost:8000/api/cdb_rest/global-tags/sPHENIX_ExampleGT_24/clone/sPHENIX_ExampleGT_25

   **Example Response** (returned with status ``200``):

   .. code-block:: json

      {
        "id": 2,
        "name": "sPHENIX_ExampleGT_25",
        "author": "admin",
        "status": "unlocked",
        "payload_lists_count": 1,
        "payload_iov_count": 2,
        "created": "2026-07-23T00:05:56.668964",
        "updated": "2026-07-23T00:05:56.668982"
      }

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

   **Example Response** (note: ``status`` is the numeric status ID here):

   .. code-block:: json

      {
        "id": 1,
        "name": "MyNewGT_v1.0",
        "author": "researcher",
        "status": 2,
        "created": "2026-07-23T00:00:26.714171",
        "updated": "2026-07-23T00:05:56.720634"
      }

   If the global tag or the new status does not exist, the request fails with an
   unhandled server error (``500`` with an HTML body).

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

   **Example Response** (returned with status ``200``):

   .. code-block:: json

      {"detail": "Global tag MyNewGT_v1.0 deleted."}

   A nonexistent name returns ``500`` with
   ``{"detail": "GlobalTag MyNewGT_v1.0 doesn't exist"}``; a locked or frozen tag
   returns ``500`` with ``{"detail": "Global Tag is locked."}``.

   .. warning::
      This operation is irreversible and will delete all associated payload lists!

   .. note::
      Global tags with status ``locked`` or ``frozen`` cannot be deleted.

List Global Tag Statuses
~~~~~~~~~~~~~~~~~~~~~~~~~

.. http:get:: /api/cdb_rest/global-tags/statuses

   List all global tag status definitions.

   **Alias of:** ``GET /api/cdb_rest/gtstatus`` (legacy path)

   **Example Request:**

   .. code-block:: bash

      curl http://localhost:8000/api/cdb_rest/global-tags/statuses

   **Example Response:**

   .. code-block:: json

      [
        {"id": 1, "name": "unlocked", "created": "2026-07-23T00:00:17.077708"},
        {"id": 2, "name": "locked", "created": "2026-07-23T00:04:43.019022"},
        {"id": 3, "name": "frozen", "created": "2026-07-23T00:04:43.062519"}
      ]

Create Global Tag Status
~~~~~~~~~~~~~~~~~~~~~~~~~

.. http:post:: /api/cdb_rest/global-tags/statuses

   Create a new global tag status definition. Statuses must be created before any
   global tag can reference them — a fresh database has none, so creating ``unlocked``
   (and typically ``locked`` and ``frozen``, which carry the semantics described under
   *Change Global Tag Status*) is the first step of any setup.

   **Alias of:** ``POST /api/cdb_rest/gtstatus`` (legacy path)

   :<json string name: Status name (required, unique)

   **Example Request:**

   .. code-block:: bash

      curl -X POST http://localhost:8000/api/cdb_rest/global-tags/statuses \
        -H "Content-Type: application/json" \
        -d '{"name": "unlocked"}'

   **Example Response** (returned with status ``200``):

   .. code-block:: json

      {"id": 1, "name": "unlocked", "created": "2026-07-23T00:00:17.077708"}

Payload Type Endpoints
======================

Payload Types define categories and structures for different kinds of conditions data.

List Payload Types
~~~~~~~~~~~~~~~~~~

.. http:get:: /api/cdb_rest/payload-types

   Retrieve all payload types. Supports :ref:`browse mode <browse-mode>` via ``?page=``.

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
          "created": "2026-07-23T00:04:43.190267"
        },
        {
          "id": 2,
          "name": "SiPixelQuality",
          "created": "2026-07-23T00:04:44.100213"
        }
      ]

Create Payload Type
~~~~~~~~~~~~~~~~~~~

.. http:post:: /api/cdb_rest/payload-types

   Create a new payload type.

   **Alias of:** ``POST /api/cdb_rest/pt`` (legacy path)

   :<json string name: Payload type name (required, unique)

   .. note::
      Although the underlying model has a ``description`` column, it is not exposed
      through the API — a ``description`` field in the request body is silently ignored.

   **Example Request:**

   .. code-block:: bash

      curl -X POST http://localhost:8000/api/cdb_rest/payload-types \
        -H "Content-Type: application/json" \
        -d '{"name": "CEMC_Calibration"}'

   **Example Response** (returned with status ``200``):

   .. code-block:: json

      {"id": 1, "name": "CEMC_Calibration", "created": "2026-07-23T00:04:43.190267"}

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

   **Example Response** (returned with status ``200``):

   .. code-block:: json

      {"detail": "Payload Type CEMC_Calibration deleted."}

   A payload type still referenced by payload lists cannot be deleted; the request
   returns ``500`` with ``{"detail": "PayloadType is used by 1 PayloadLists"}``.

Payload List Endpoints
======================

Payload Lists link Global Tags to Payload Types and serve as containers for payload versions.

List Payload Lists
~~~~~~~~~~~~~~~~~~

.. http:get:: /api/cdb_rest/payload-lists

   Retrieve all payload lists, each with its payload IOVs fully nested (this can be
   large). Supports :ref:`browse mode <browse-mode>` via ``?page=``, which returns
   flat rows with an ``iov_count`` instead of nested IOVs, filterable by
   ``?global_tag=`` and ``?payload_type=``.

   **Alias of:** ``GET /api/cdb_rest/pl`` (legacy path)

   **Example Request:**

   .. code-block:: bash

      curl http://localhost:8000/api/cdb_rest/payload-lists

Get Payload Lists for Global Tag
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. http:get:: /api/cdb_rest/global-tags/(str:gt_name)/payload-lists

   Retrieve all payload lists associated with a specific global tag, as a
   ``{payload_type: payload_list_name}`` map.

   **Alias of:** ``GET /api/cdb_rest/gtPayloadLists/(str:gt_name)`` (legacy path)

   :param gt_name: Global tag name
   :type gt_name: string

   **Example Request:**

   .. code-block:: bash

      curl http://localhost:8000/api/cdb_rest/global-tags/sPHENIX_ExampleGT_24/payload-lists

   **Example Response:**

   .. code-block:: json

      {"Beam": "Beam_210", "CEMC_Calibration": "CEMC_Calibration_42"}

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
        "created": "2026-07-23T00:05:09.713172"
      }

   If the referenced payload type does not exist, the request fails with an unhandled
   server error (``500`` with an HTML body).

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
        "created": "2022-02-21T15:10:00.000000"
      }

   Unknown names return ``404`` with ``{"detail": "Not found."}``.

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

   **Example Response** (returned with status ``200``):

   .. code-block:: json

      {
        "id": 42,
        "name": "CEMC_Calibration_42",
        "global_tag": "sPHENIX_ExampleGT_24",
        "payload_type": "CEMC_Calibration",
        "created": "2026-07-23T00:05:09.713172"
      }

   If the global tag or payload list does not exist, the request fails with an
   unhandled server error (``500`` with an HTML body).

Delete Payload List
~~~~~~~~~~~~~~~~~~~

.. http:delete:: /api/cdb_rest/payload-lists/(str:name)/delete

   Delete a payload list. A list that still contains payload IOVs cannot be deleted —
   the request returns ``500`` with ``{"detail": "PayloadList contains 2 PayloadIOVs"}``.

   **Alias of:** ``DELETE /api/cdb_rest/deletePayloadList/(str:name)`` (legacy path)

   :param name: Payload list name
   :type name: string

   **Example Request:**

   .. code-block:: bash

      curl -X DELETE http://localhost:8000/api/cdb_rest/payload-lists/CEMC_Calibration_42/delete

   **Example Response** (returned with status ``200``; the message says "Payload Type"
   due to a quirk in the implementation, but it is the payload *list* that is deleted):

   .. code-block:: json

      {"detail": "Payload Type CEMC_Calibration_42 deleted."}

Payload IOV Endpoints
=====================

Payload IOVs (Intervals of Validity) represent individual conditions data entries with their validity ranges.

List Payload IOVs
~~~~~~~~~~~~~~~~~

.. http:get:: /api/cdb_rest/payload-iovs

   Retrieve all payload IOVs in the system (this can be very large). Supports
   :ref:`browse mode <browse-mode>` via ``?page=``, which returns flat rows including
   the ``global_tag`` and ``payload_type`` names, filterable by ``?payload_list=``,
   ``?global_tag=`` and ``?payload_type=``.

   **Alias of:** ``GET /api/cdb_rest/piov`` (legacy path)

   **Example Request:**

   .. code-block:: bash

      curl 'http://localhost:8000/api/cdb_rest/payload-iovs?page=1&global_tag=sPHENIX_ExampleGT_24'

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
        ["Beam", "D0DXMagnets.dat", "e99a18c428cb38d5f260853678922e03", null,
         0, 999999, 9223372036854775807, 9223372036854775807, null]
      ]

   **Example Response (shape=dict):**

   .. code-block:: json

      [
        {
          "payload_type_name": "Beam",
          "payload_url": "D0DXMagnets.dat",
          "checksum": "e99a18c428cb38d5f260853678922e03",
          "size": null,
          "major_iov": 0,
          "minor_iov": 999999,
          "major_iov_end": 9223372036854775807,
          "minor_iov_end": 9223372036854775807,
          "revision": null
        }
      ]

   .. note::
      The ``size`` and ``revision`` (``extra``) columns exist in the database but
      cannot be set through the REST API, so they are ``null`` unless populated
      by other means.

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
   :<json int major_iov: Major IOV start (required)
   :<json int minor_iov: Minor IOV start (required)
   :<json int major_iov_end: Major IOV end (optional, defaults to ``sys.maxsize``)
   :<json int minor_iov_end: Minor IOV end (optional, defaults to ``sys.maxsize``)

   .. note::
      A ``size`` field in the request body is silently ignored — the serializer does
      not expose the model's ``size`` column.

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
          "major_iov": 0,
          "minor_iov": 1000,
          "major_iov_end": 0,
          "minor_iov_end": 2000
        }'

   **Example Response** (returned with status ``200``):

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
        "inserted": "2026-07-23T00:05:09.831925"
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

   On success the endpoint returns ``200`` with an **empty** response body. Note that
   ``checksum`` cannot be provided through this endpoint and is left unset.

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

   **Example Response** (the updated payload IOV, returned with status ``200``):

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
        "payload_list": "Beam_210",
        "inserted": "2026-07-23T00:05:09.831925"
      }

   If the payload list or the payload IOV does not exist, the request fails with an
   unhandled server error (``500`` with an HTML body).

Delete Payload IOV
~~~~~~~~~~~~~~~~~~

.. http:delete:: /api/cdb_rest/payload-iovs/(str:gtName)/(str:payloadType)/(int:majorIOV)/(int:minorIOV)/delete

   Delete a single **open-ended** payload IOV. The omitted end values default to
   ``sys.maxsize``, so this form only matches an IOV whose ``major_iov_end`` and
   ``minor_iov_end`` are both ``sys.maxsize``.

   **Alias of:** ``DELETE /api/cdb_rest/deletePayloadIOV/(str:gtName)/(str:payloadType)/(int:majorIOV)/(int:minorIOV)`` (legacy path)

   :param gtName: Global tag name
   :param payloadType: Payload type name
   :param majorIOV: Major IOV value
   :param minorIOV: Minor IOV value

.. http:delete:: /api/cdb_rest/payload-iovs/(str:gtName)/(str:payloadType)/(int:majorIOV)/(int:minorIOV)/(int:majorIOVEnd)/(int:minorIOVEnd)/delete

   Delete the single payload IOV whose start **and** end values match exactly. This is
   **not** a range delete — it never removes more than one IOV.

   **Alias of:** ``DELETE /api/cdb_rest/deletePayloadIOV/(str:gtName)/(str:payloadType)/(int:majorIOV)/(int:minorIOV)/(int:majorIOVEnd)/(int:minorIOVEnd)`` (legacy path)

   **Example Request:**

   .. code-block:: bash

      # Delete an open-ended IOV (ends implicitly sys.maxsize)
      curl -X DELETE http://localhost:8000/api/cdb_rest/payload-iovs/sPHENIX_ExampleGT_24/Beam/0/1000/delete

      # Delete an IOV with explicit end values (exact match required)
      curl -X DELETE http://localhost:8000/api/cdb_rest/payload-iovs/sPHENIX_ExampleGT_24/Beam/0/1000/0/2000/delete

   **Example Response** (returned with status ``200``):

   .. code-block:: json

      {"detail": "PayloadIOV calibration_data_v1.2.root deleted."}

   If no IOV matches all parameters exactly, the request returns ``500`` with
   ``{"detail": "PayloadIOV with given parameters doesn't exist"}``. IOVs in a
   ``frozen`` global tag cannot be deleted; ``locked`` tags allow deletion.

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

   Read-only access to the server's ``CDB_*`` configuration values.

   **Alias of:** ``GET /api/cdb_rest/user_settings/(str:name)/`` (legacy path)

   :param name: Setting name, e.g. ``CDB_IOV_MODE``
   :type name: string

   **Example Request:**

   .. code-block:: bash

      curl http://localhost:8000/api/cdb_rest/settings/CDB_IOV_MODE/

   **Example Response:**

   .. code-block:: json

      {"CDB_IOV_MODE": "continuous"}

   .. warning::
      Only ``CDB_``-prefixed variables that are actually **set in the server's
      environment** are exposed. Settings that merely fall back to an in-code default
      (e.g. ``CDB_IOV_MODE`` when the environment variable is unset, as in the default
      Docker setup) return ``404`` like unknown names:
      ``{"detail": "Setting 'CDB_IOV_MODE' not found."}``.

Lookup by ID
============

In addition to the name-based endpoints above, each resource can be retrieved by its
numeric primary key. Unknown IDs return ``404`` with ``{"detail": "Not found."}``.

.. http:get:: /api/cdb_rest/gt/(int:id)

   Retrieve a global tag by ID (full nested representation, no alias path).

.. http:get:: /api/cdb_rest/payload-lists/(int:id)

   Retrieve a payload list by ID. **Alias of:** ``GET /api/cdb_rest/pl/(int:id)``.
   Note: ``global_tag`` and ``payload_type`` are returned as numeric IDs here.

.. http:get:: /api/cdb_rest/payload-iovs/(int:id)

   Retrieve a payload IOV by ID. **Alias of:** ``GET /api/cdb_rest/piov/(int:id)``.

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
     - Successful request — including creates (POST), updates (PUT) and deletes (DELETE)
   * - 400
     - Bad Request
     - Invalid request data, missing required fields, or duplicate names (serializer validation)
   * - 403
     - Forbidden
     - Rejected by the configured permission plugin
   * - 404
     - Not Found
     - Detail lookup by ID/name failed, or unknown setting name
   * - 500
     - Internal Server Error
     - Business-logic errors (missing referenced resources, locked/frozen global tags, IOV conflicts) and unhandled server errors

Error Response Format
~~~~~~~~~~~~~~~~~~~~~

Error responses use a single ``detail`` field:

.. code-block:: json

   {
     "detail": "GlobalTag NonExistentGT doesn't exist"
   }

.. note::
   Most business-logic errors (missing resources, immutable global tags, IOV conflicts) are
   currently returned with status ``500``. In addition, some
   "referenced resource not found" cases (e.g. creating a global tag with a nonexistent
   status, attaching to a nonexistent payload list, cloning a nonexistent global tag) are
   unhandled in the code and return a generic ``500`` with an **HTML** error page instead
   of a JSON body.

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

1. **Batch Operations**: Use bulk endpoint for multiple operations
2. **Appropriate IOV Ranges**: Use precise IOV ranges to limit result sets
3. **Caching**: Cache frequently accessed data on the client side