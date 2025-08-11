.. _api-docs:

=================
API Documentation
=================

The Nopayloaddb project provides a comprehensive RESTful API for managing payloads, global tags, payload types, and associated conditions database operations. The API enables clients to perform CRUD operations on these resources with full support for complex queries and bulk operations.

.. contents:: Table of Contents
   :local:
   :depth: 2

Quick Start
===========

.. note::
   **Try it now**: If you have Nopayloaddb running locally, you can test these examples immediately!

**Base URL**

All API endpoints are prefixed with ``/api/cdb_rest/``. For example:

.. tabs::

   .. tab:: Local Development
   
      .. code-block:: text
      
         http://localhost:8000/api/cdb_rest/

   .. tab:: Production
   
      .. code-block:: text
      
         http://nopayloaddb-nopayloaddb.apps.sdcc.bnl.gov/api/cdb_rest/

   .. tab:: Test Environment
   
      .. code-block:: text
      
         http://npdb-test-test.apps.sdcc.bnl.gov/api/cdb_rest/

**Quick Test**

Verify your installation with this simple command:

.. code-block:: bash

   curl http://localhost:8000/api/cdb_rest/gt

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
   **Development Mode**: By default, authentication is disabled for development. See :doc:`deployment` for production authentication setup.

Currently, authentication is disabled in the default configuration. For production deployments, the API supports:

- **JWT Token Authentication**
- **Django REST Framework Token Authentication**
- **Custom Authentication Backends**

When authentication is enabled, include the token in your requests:

.. code-block:: bash

   curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
        http://localhost:8000/api/cdb_rest/gt

Global Tag Endpoints
====================

Global Tags represent named collections of payload versions for consistent conditions management.

List All Global Tags
~~~~~~~~~~~~~~~~~~~~~

.. http:get:: /api/cdb_rest/globalTags

   Retrieve a list of all global tags in the system.

   **Example Request:**

   .. code-block:: bash

      curl http://localhost:8000/api/cdb_rest/globalTags

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

.. http:get:: /api/cdb_rest/globalTag/(str:name)

   Retrieve detailed information about a specific global tag.

   :param name: Global tag name
   :type name: string

   **Example Request:**

   .. code-block:: bash

      curl http://localhost:8000/api/cdb_rest/globalTag/sPHENIX_ExampleGT_24

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

   :<json string name: Global tag name (required, unique)
   :<json string author: Author/creator name (required)
   :<json string description: Description of the global tag (required)
   :<json int status: Status ID (required)

   **Example Request:**

   .. code-block:: bash

      curl -X POST http://localhost:8000/api/cdb_rest/gt \
        -H "Content-Type: application/json" \
        -d '{
          "name": "MyNewGT_v1.0",
          "author": "researcher",
          "description": "New global tag for calibration campaign",
          "status": 1
        }'

   **Example Response:**

   .. code-block:: json

      {
        "id": 2,
        "name": "MyNewGT_v1.0",
        "author": "researcher",
        "description": "New global tag for calibration campaign",
        "status": 1,
        "created": "2025-01-15T10:30:00.000000Z"
      }

Clone Global Tag
~~~~~~~~~~~~~~~~

.. http:post:: /api/cdb_rest/cloneGlobalTag/(str:source_name)/(str:target_name)

   Create a copy of an existing global tag with all its payload lists.

   :param source_name: Name of the global tag to clone
   :param target_name: Name for the new global tag
   :type source_name: string
   :type target_name: string

   **Example Request:**

   .. code-block:: bash

      curl -X POST http://localhost:8000/api/cdb_rest/cloneGlobalTag/sPHENIX_ExampleGT_24/sPHENIX_ExampleGT_25

Change Global Tag Status
~~~~~~~~~~~~~~~~~~~~~~~~~

.. http:put:: /api/cdb_rest/gt_change_status/(str:name)/(int:status)

   Update the status of a global tag.

   :param name: Global tag name
   :param status: New status ID
   :type name: string
   :type status: integer

   **Example Request:**

   .. code-block:: bash

      curl -X PUT http://localhost:8000/api/cdb_rest/gt_change_status/MyNewGT_v1.0/2

Delete Global Tag
~~~~~~~~~~~~~~~~~

.. http:delete:: /api/cdb_rest/deleteGlobalTag/(str:name)

   Delete a global tag and all associated payload lists.

   :param name: Global tag name
   :type name: string

   **Example Request:**

   .. code-block:: bash

      curl -X DELETE http://localhost:8000/api/cdb_rest/deleteGlobalTag/MyNewGT_v1.0

   .. warning::
      This operation is irreversible and will delete all associated payload lists!

Global Tag Status Management
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. http:get:: /api/cdb_rest/gtstatus
.. http:post:: /api/cdb_rest/gtstatus

   Manage global tag status definitions.

   **Example Request (GET):**

   .. code-block:: bash

      curl http://localhost:8000/api/cdb_rest/gtstatus

Payload Type Endpoints
======================

Payload Types define categories and structures for different kinds of conditions data.

List Payload Types
~~~~~~~~~~~~~~~~~~

.. http:get:: /api/cdb_rest/pt

   Retrieve all payload types.

   **Example Request:**

   .. code-block:: bash

      curl http://localhost:8000/api/cdb_rest/pt

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

.. http:post:: /api/cdb_rest/pt

   Create a new payload type.

   :<json string name: Payload type name (required, unique)
   :<json string description: Description of the payload type (optional)

   **Example Request:**

   .. code-block:: bash

      curl -X POST http://localhost:8000/api/cdb_rest/pt \
        -H "Content-Type: application/json" \
        -d '{
          "name": "CEMC_Calibration",
          "description": "Electromagnetic calorimeter calibration constants"
        }'

Delete Payload Type
~~~~~~~~~~~~~~~~~~~

.. http:delete:: /api/cdb_rest/deletePayloadType/(str:name)

   Delete a payload type.

   :param name: Payload type name
   :type name: string

   **Example Request:**

   .. code-block:: bash

      curl -X DELETE http://localhost:8000/api/cdb_rest/deletePayloadType/CEMC_Calibration

Payload List Endpoints
======================

Payload Lists link Global Tags to Payload Types and serve as containers for payload versions.

List Payload Lists
~~~~~~~~~~~~~~~~~~

.. http:get:: /api/cdb_rest/pl

   Retrieve all payload lists.

   **Example Request:**

   .. code-block:: bash

      curl http://localhost:8000/api/cdb_rest/pl

Get Payload Lists for Global Tag
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. http:get:: /api/cdb_rest/gtPayloadLists/(str:gt_name)

   Retrieve all payload lists associated with a specific global tag.

   :param gt_name: Global tag name
   :type gt_name: string

   **Example Request:**

   .. code-block:: bash

      curl http://localhost:8000/api/cdb_rest/gtPayloadLists/sPHENIX_ExampleGT_24

Create Payload List
~~~~~~~~~~~~~~~~~~~

.. http:post:: /api/cdb_rest/pl

   Create a new payload list.

   :<json string name: Payload list name (required, unique)
   :<json string description: Description (optional)
   :<json int global_tag: Global tag ID (required)
   :<json int payload_type: Payload type ID (required)

   **Example Request:**

   .. code-block:: bash

      curl -X POST http://localhost:8000/api/cdb_rest/pl \
        -H "Content-Type: application/json" \
        -d '{
          "name": "CEMC_Calibration_v1.0",
          "description": "First version of CEMC calibration",
          "global_tag": 1,
          "payload_type": 3
        }'

Attach Payload List to Global Tag
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. http:post:: /api/cdb_rest/pl_attach

   Attach an existing payload list to a global tag.

   :<json string global_tag: Global tag name (required)
   :<json string payload_list: Payload list name (required)

   **Example Request:**

   .. code-block:: bash

      curl -X POST http://localhost:8000/api/cdb_rest/pl_attach \
        -H "Content-Type: application/json" \
        -d '{
          "global_tag": "sPHENIX_ExampleGT_24",
          "payload_list": "CEMC_Calibration_v1.0"
        }'

Delete Payload List
~~~~~~~~~~~~~~~~~~~

.. http:delete:: /api/cdb_rest/deletePayloadList/(str:name)

   Delete a payload list and all associated payload IOVs.

   :param name: Payload list name
   :type name: string

   **Example Request:**

   .. code-block:: bash

      curl -X DELETE http://localhost:8000/api/cdb_rest/deletePayloadList/CEMC_Calibration_v1.0

Payload IOV Endpoints
=====================

Payload IOVs (Intervals of Validity) represent individual conditions data entries with their validity ranges.

Main Payload Query Endpoint
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. http:get:: /api/cdb_rest/payloadiovs/

   **Primary endpoint** for querying payload IOVs. This is the main endpoint for retrieving conditions data.

   :query gtName: Global tag name (required)
   :query majorIOV: Major IOV value (required)
   :query minorIOV: Minor IOV value (required)
   :query payloadType: Filter by payload type name (optional)

   **Example Request:**

   .. code-block:: bash

      # Basic query
      curl 'http://localhost:8000/api/cdb_rest/payloadiovs/?gtName=sPHENIX_ExampleGT_24&majorIOV=0&minorIOV=999999'

      # Filter by payload type
      curl 'http://localhost:8000/api/cdb_rest/payloadiovs/?gtName=sPHENIX_ExampleGT_24&majorIOV=0&minorIOV=999999&payloadType=Beam'

   **Example Response:**

   .. code-block:: json

      [
        {
          "id": 210,
          "name": "Beam_210",
          "global_tag": "sPHENIX_ExampleGT_24",
          "payload_type": "Beam",
          "payload_iov": [
            {
              "id": 13425388,
              "payload_url": "D0DXMagnets.dat",
              "major_iov": 0,
              "minor_iov": 999999,
              "major_iov_end": 0,
              "minor_iov_end": 999999,
              "payload_list": "Beam_210",
              "checksum": "sha256:abc123...",
              "size": 1024,
              "description": "Beam parameters for run period",
              "created": "2022-02-21T15:28:20.949696Z"
            }
          ],
          "created": "2022-02-21T15:17:06.481186Z"
        }
      ]

Alternative Query Endpoints
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. http:get:: /api/cdb_rest/payloadiovs_orm_orderby/

   Alternative ORM-based query endpoint with ordering.

.. http:get:: /api/cdb_rest/payloadiovs_orm_max/

   Get maximum IOV values for optimization.

Create Payload IOV
~~~~~~~~~~~~~~~~~~

.. http:post:: /api/cdb_rest/piov

   Create a single payload IOV.

   :<json string payload_url: URL/path to payload file (required)
   :<json string checksum: File checksum (optional, recommended)
   :<json int size: File size in bytes (optional)
   :<json int major_iov: Major IOV start (required)
   :<json int minor_iov: Minor IOV start (required)
   :<json int major_iov_end: Major IOV end (optional)
   :<json int minor_iov_end: Minor IOV end (optional)
   :<json int payload_list: Payload list ID (required)
   :<json string description: Description (optional)

   **Example Request:**

   .. code-block:: bash

      curl -X POST http://localhost:8000/api/cdb_rest/piov \
        -H "Content-Type: application/json" \
        -d '{
          "payload_url": "calibration_data_v1.2.root",
          "checksum": "sha256:abcd1234ef567890...",
          "size": 2048000,
          "major_iov": 0,
          "minor_iov": 1000,
          "major_iov_end": 0,
          "minor_iov_end": 2000,
          "payload_list": 1,
          "description": "Calibration data for runs 1000-2000"
        }'

Bulk Create Payload IOVs
~~~~~~~~~~~~~~~~~~~~~~~~

.. http:post:: /api/cdb_rest/bulk_piov

   Create multiple payload IOVs in a single operation for improved performance.

   **Example Request:**

   .. code-block:: bash

      curl -X POST http://localhost:8000/api/cdb_rest/bulk_piov \
        -H "Content-Type: application/json" \
        -d '[
          {
            "payload_url": "data_run1000.root",
            "checksum": "sha256:1111...",
            "major_iov": 0,
            "minor_iov": 1000,
            "major_iov_end": 0,
            "minor_iov_end": 1500,
            "payload_list": 1
          },
          {
            "payload_url": "data_run1500.root", 
            "checksum": "sha256:2222...",
            "major_iov": 0,
            "minor_iov": 1500,
            "major_iov_end": 0,
            "minor_iov_end": 2000,
            "payload_list": 1
          }
        ]'

Attach Payload IOV to List
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. http:post:: /api/cdb_rest/piov_attach

   Attach an existing payload IOV to a payload list.

   :<json string payload_list: Payload list name (required)
   :<json int piov_id: Payload IOV ID (required)

Delete Payload IOV
~~~~~~~~~~~~~~~~~~

.. http:delete:: /api/cdb_rest/deletePayloadIOV/(str:gtName)/(str:payloadType)/(int:majorIOV)/(int:minorIOV)

   Delete a specific payload IOV.

   :param gtName: Global tag name
   :param payloadType: Payload type name
   :param majorIOV: Major IOV value
   :param minorIOV: Minor IOV value

.. http:delete:: /api/cdb_rest/deletePayloadIOV/(str:gtName)/(str:payloadType)/(int:majorIOV)/(int:minorIOV)/(int:majorIOVEnd)/(int:minorIOVEnd)

   Delete payload IOVs in a range.

   **Example Request:**

   .. code-block:: bash

      # Delete specific IOV
      curl -X DELETE http://localhost:8000/api/cdb_rest/deletePayloadIOV/sPHENIX_ExampleGT_24/Beam/0/1000

      # Delete range of IOVs
      curl -X DELETE http://localhost:8000/api/cdb_rest/deletePayloadIOV/sPHENIX_ExampleGT_24/Beam/0/1000/0/2000

Utility Endpoints
=================

Test and Utility Functions
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. http:get:: /api/cdb_rest/timeout

   Test endpoint for timeout testing and system monitoring.

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
   curl 'http://localhost:8000/api/cdb_rest/payloadiovs/?gtName=Production_GT_v2.1&majorIOV=0&minorIOV=12345'

Get Specific Detector Conditions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Get only beam conditions for a run
   curl 'http://localhost:8000/api/cdb_rest/payloadiovs/?gtName=Production_GT_v2.1&majorIOV=0&minorIOV=12345&payloadType=Beam'

List All Available Global Tags
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # See what global tags are available
   curl http://localhost:8000/api/cdb_rest/globalTags | jq '.[].name'

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

Error responses include detailed information:

.. code-block:: json

   {
     "error": "Global tag not found",
     "code": 404,
     "details": "Global tag 'NonExistentGT' does not exist in the database",
     "timestamp": "2025-01-15T10:30:00.000000Z"
   }

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

1. **Use Specific Queries**: Include payload type filters when possible
2. **Batch Operations**: Use bulk endpoints for multiple operations
3. **Appropriate IOV Ranges**: Use precise IOV ranges to limit result sets
4. **Caching**: Cache frequently accessed data on the client side

Database Considerations
~~~~~~~~~~~~~~~~~~~~~~~

- The main ``/payloadiovs/`` endpoint is optimized for complex queries
- Bulk operations are significantly faster than individual requests
- Consider using read replicas for high-load query scenarios

Integration Examples
====================

Python Integration
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import requests
   
   class NopayloaddbClient:
       def __init__(self, base_url):
           self.base_url = base_url.rstrip('/')
           self.api_base = f"{self.base_url}/api/cdb_rest"
       
       def get_conditions(self, gt_name, major_iov, minor_iov, payload_type=None):
           """Get conditions for a specific global tag and IOV."""
           params = {
               'gtName': gt_name,
               'majorIOV': major_iov,
               'minorIOV': minor_iov
           }
           if payload_type:
               params['payloadType'] = payload_type
           
           response = requests.get(f"{self.api_base}/payloadiovs/", params=params)
           response.raise_for_status()
           return response.json()
       
       def create_global_tag(self, name, author, description, status_id=1):
           """Create a new global tag."""
           data = {
               'name': name,
               'author': author,
               'description': description,
               'status': status_id
           }
           response = requests.post(f"{self.api_base}/gt", json=data)
           response.raise_for_status()
           return response.json()
   
   # Usage example
   client = NopayloaddbClient('http://localhost:8000')
   conditions = client.get_conditions('sPHENIX_ExampleGT_24', 0, 999999)
   print(f"Found conditions for {len(conditions)} payload types")

Shell Script Integration
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   #!/bin/bash
   
   API_BASE="http://localhost:8000/api/cdb_rest"
   GT_NAME="Production_GT_v2.1"
   
   # Function to get conditions for a run
   get_conditions() {
       local gt_name=$1
       local run_number=$2
       
       curl -s "${API_BASE}/payloadiovs/?gtName=${gt_name}&majorIOV=0&minorIOV=${run_number}" \
           | jq -r '.[] | "\(.payload_type): \(.payload_iov[0].payload_url)"'
   }
   
   # Function to list available global tags
   list_global_tags() {
       curl -s "${API_BASE}/globalTags" | jq -r '.[].name'
   }
   
   # Usage
   echo "Available Global Tags:"
   list_global_tags
   
   echo -e "\nConditions for run 12345:"
   get_conditions "$GT_NAME" 12345

API Versioning
==============

.. note::
   **Current Version**: The API is currently at version 1.0. Future versions will maintain backward compatibility where possible.

The API follows semantic versioning principles:

- **Major versions** (e.g., 1.0 → 2.0): Breaking changes
- **Minor versions** (e.g., 1.0 → 1.1): New features, backward compatible  
- **Patch versions** (e.g., 1.0.0 → 1.0.1): Bug fixes, backward compatible

Future versions will be accessible via URL versioning:

.. code-block:: text

   /api/v2/cdb_rest/  # Future version 2.0

Rate Limiting
=============

.. note::
   **Development**: Rate limiting is not enforced in development mode.

Production deployments may implement rate limiting:

- **Per-user limits**: Authenticated users may have different limits
- **Per-IP limits**: Anonymous requests may be limited by IP address
- **Per-endpoint limits**: Some endpoints may have specific limits

Rate limit information is included in response headers:

.. code-block:: text

   X-RateLimit-Limit: 1000
   X-RateLimit-Remaining: 999
   X-RateLimit-Reset: 1642694400

Next Steps
==========

- **Usage Examples**: See :doc:`usage` for practical workflow examples
- **Development**: Check :doc:`development` for API development guidelines
- **Architecture**: Learn about the system design in :doc:`architecture`
- **Deployment**: Production API setup in :doc:`deployment`

.. tip::
   **Interactive API Exploration**: Once you have Nopayloaddb running, you can explore the API interactively by visiting http://localhost:8000/api/cdb_rest/ in your browser (if DRF browsable API is enabled).