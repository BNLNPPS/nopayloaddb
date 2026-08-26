.. _usage:

Usage Guide
===========

This guide provides practical examples of how to use the Nopayloaddb API for common operations.

Getting Started
---------------

Before using the API, ensure you have the service running. See :ref:`install` for setup instructions.

**Service URLs**

- Local development: ``http://localhost:8000``

**API Base Path**

All API endpoints are prefixed with ``/api/cdb_rest/``.

Common Workflows
----------------

1. Querying Payloads
~~~~~~~~~~~~~~~~~~~~

The most common operation is querying for payloads based on a Global Tag and IOV.

**Basic Query**

.. code-block:: bash

   curl 'http://localhost:8000/api/cdb_rest/payloadiovs/?gtName=sPHENIX_ExampleGT_24&majorIOV=0&minorIOV=999999'

**Response**

The endpoint returns one row per payload list: the latest payload IOV valid at the requested
point. Each row contains payload type name, payload URL, checksum, size, major IOV,
minor IOV, major IOV end, minor IOV end, and revision:

.. code-block:: json

   [
     ["Beam", "D0DXMagnets.dat", "e99a18c428cb38d5f260853678922e03", 1024,
      0, 999999, 9223372036854775807, 9223372036854775807, null]
   ]

**Dictionary-Shaped Response**

Add ``shape=dict`` to receive named fields instead of positional rows:

.. code-block:: bash

   curl 'http://localhost:8000/api/cdb_rest/payloadiovs/?gtName=sPHENIX_ExampleGT_24&majorIOV=0&minorIOV=999999&shape=dict'

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

2. Managing Global Tags
~~~~~~~~~~~~~~~~~~~~~~~~

**List All Global Tags**

.. code-block:: bash

   curl http://localhost:8000/api/cdb_rest/globalTags

**Get Specific Global Tag**

.. code-block:: bash

   curl http://localhost:8000/api/cdb_rest/globalTag/sPHENIX_ExampleGT_24


**Create New Global Tag Status**

.. code-block:: bash

    curl -X POST http://localhost:8000/api/cdb_rest/gtstatus \
      -H "Content-Type: application/json" \
      -d '{
        "name": "Open"
      }'


**Create New Global Tag**

The ``status`` field is the **name** of an existing global tag status:

.. code-block:: bash

   curl -X POST http://localhost:8000/api/cdb_rest/gt \
     -H "Content-Type: application/json" \
     -d '{
       "name": "MyNewGT",
       "author": "username",
       "status": "Open"
     }'

**Change Global Tag Status**

.. code-block:: bash

   curl -X PUT http://localhost:8000/api/cdb_rest/gt_change_status/MyNewGT/locked

**Clone Global Tag**

.. code-block:: bash

   curl -X POST http://localhost:8000/api/cdb_rest/cloneGlobalTag/sPHENIX_ExampleGT_24/MyClonedGT

3. Managing Payload Types
~~~~~~~~~~~~~~~~~~~~~~~~~~

**List Payload Types**

.. code-block:: bash

   curl http://localhost:8000/api/cdb_rest/pt

**Create Payload Type**

.. code-block:: bash

   curl -X POST http://localhost:8000/api/cdb_rest/pt \
     -H "Content-Type: application/json" \
     -d '{
       "name": "MyPayloadType",
       "description": "Description of my payload type"
     }'

4. Managing Payload Lists
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Create Payload List**

The name is auto-generated from the payload type name and an internal sequence ID; only the
payload type name is required. The list is created detached from any global tag:

.. code-block:: bash

   curl -X POST http://localhost:8000/api/cdb_rest/pl \
     -H "Content-Type: application/json" \
     -d '{
       "payload_type": "MyPayloadType"
     }'

**Attach Payload List to Global Tag**

Use the generated name returned by the previous call:

.. code-block:: bash

   curl -X PUT http://localhost:8000/api/cdb_rest/pl_attach \
     -H "Content-Type: application/json" \
     -d '{
       "global_tag": "MyGlobalTag",
       "payload_list": "MyPayloadType_123"
     }'

5. Managing Payload IOVs
~~~~~~~~~~~~~~~~~~~~~~~~~

**Create Single Payload IOV**

The IOV is created detached; attach it to a payload list in a second step. End IOVs default
to ``sys.maxsize`` (open-ended) when omitted. Range validation depends on ``CDB_IOV_MODE``
(``continuous`` by default — end must be strictly greater than start):

.. code-block:: bash

   curl -X POST http://localhost:8000/api/cdb_rest/piov \
     -H "Content-Type: application/json" \
     -d '{
       "payload_url": "calibration_data_v1.root",
       "checksum": "sha256:abcd1234...",
       "size": 1024000,
       "major_iov": 0,
       "minor_iov": 1000,
       "major_iov_end": 0,
       "minor_iov_end": 2000
     }'

**Attach Payload IOV to a Payload List**

Overlapping IOVs in the list are split or trimmed if the global tag is unlocked; conflicting
IOVs are rejected if the global tag is locked:

.. code-block:: bash

   curl -X PUT http://localhost:8000/api/cdb_rest/piov_attach \
     -H "Content-Type: application/json" \
     -d '{
       "payload_list": "MyPayloadType_123",
       "piov_id": 1
     }'

**Bulk Create Payload IOVs**

Bulk-created IOVs are attached directly to a payload list (by name) and are always
open-ended (end IOVs set to ``sys.maxsize``):

.. code-block:: bash

   curl -X POST http://localhost:8000/api/cdb_rest/bulk_piov \
     -H "Content-Type: application/json" \
     -d '[
       {
         "payload_url": "data1.root",
         "major_iov": 0,
         "minor_iov": 1000,
         "payload_list": "MyPayloadType_123"
       },
       {
         "payload_url": "data2.root",
         "major_iov": 0,
         "minor_iov": 1500,
         "payload_list": "MyPayloadType_123"
       }
     ]'

6. Reading Server Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Any ``CDB_*`` environment variable set on the server can be read through the settings
endpoint:

.. code-block:: bash

   curl http://localhost:8000/api/cdb_rest/user_settings/CDB_IOV_MODE/
   # {"CDB_IOV_MODE": "continuous"}

Best Practices
--------------

IOV Management
~~~~~~~~~~~~~~~

**IOV Ranges**

- Use non-overlapping IOV ranges within a payload list
- Ensure continuous coverage for time-dependent data
- Use appropriate major/minor IOV values for your experiment's time model

**Payload URLs**

- Use descriptive, unique filenames
- Include version information in filenames
- Store payload files in reliable, accessible storage

Global Tag Versioning
~~~~~~~~~~~~~~~~~~~~~~

**Naming Convention**

- Use descriptive names that indicate purpose and version
- Include experiment name, data-taking period, and version
- Example: ``sPHENIX_Run23_Commissioning_v1.0``

**Status Management**

- Use appropriate status values to indicate global tag readiness
- Test global tags before marking as production-ready
- Document changes and improvements

Error Handling
--------------

Common HTTP Status Codes
~~~~~~~~~~~~~~~~~~~~~~~~~

- **200 OK**: Successful request
- **201 Created**: Resource created successfully
- **400 Bad Request**: Invalid request data
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: Server error

**Example Error Response**

Errors are returned as a single ``detail`` field. Note that most business-logic errors
(missing resources, locked/frozen global tags, IOV conflicts) currently return status
``500``:

.. code-block:: json

   {
     "detail": "GlobalTag NonExistentGT doesn't exist"
   }

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~~

**No Payloads Found**

- Check that the global tag name is correct
- Verify that the IOV values are within the payload's validity range
- Ensure the global tag contains payload lists for the requested payload type

**Authentication Errors**

- Write operations (POST/PUT/PATCH/DELETE) require a JWT bearer token when ``CDB_AUTH_CLASS`` is set
- Verify the token is signed with the server's ``JWT_SECRET`` (HS256) and not expired
- A ``403 Permission denied`` on writes indicates the configured permission plugin
  (``CDB_PERMISSION_PLUGIN_CLASS``) rejected the request for that global tag or payload list

**Database Connection Issues**

- Check database connectivity and credentials
- Verify that migrations have been applied
- Check database server status

Performance Optimization
------------------------

Query Optimization
~~~~~~~~~~~~~~~~~~~

**Use Specific Queries**

- Include payload type filters when possible
- Use appropriate IOV ranges to limit results
- Prefer the main ``/payloadiovs/`` endpoint for complex queries

**Batch Operations**

- Use bulk creation endpoints for multiple payloads
- Minimize the number of individual API calls
- Consider caching frequently accessed data

**Database Considerations**

- Monitor query performance
- Use appropriate database indexes
- Consider read replicas for high-load scenarios

Integration Examples
--------------------

Python Client Example
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import requests
   import json

   class NopayloaddbClient:
       def __init__(self, base_url):
           self.base_url = base_url.rstrip('/')
           self.api_base = f"{self.base_url}/api/cdb_rest"
       
       def get_payloads(self, gt_name, major_iov, minor_iov):
           """Get payloads for a specific global tag and IOV."""
           params = {
               'gtName': gt_name,
               'majorIOV': major_iov,
               'minorIOV': minor_iov,
               'shape': 'dict'  # get named fields instead of positional rows
           }
           response = requests.get(f"{self.api_base}/payloadiovs/", params=params)
           response.raise_for_status()
           return response.json()

       def create_global_tag(self, name, author, status='unlocked'):
           """Create a new global tag."""
           data = {
               'name': name,
               'author': author,
               'status': status  # status name, must exist in /gtstatus
           }
           response = requests.post(f"{self.api_base}/gt", json=data)
           response.raise_for_status()
           return response.json()

   # Usage
   client = NopayloaddbClient('http://localhost:8000')
   payloads = client.get_payloads('sPHENIX_ExampleGT_24', 0, 999999)
   print(f"Found {len(payloads)} payload types")

Shell Script Example
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   #!/bin/bash
   
   BASE_URL="http://localhost:8000/api/cdb_rest"
   GT_NAME="sPHENIX_ExampleGT_24"
   MAJOR_IOV=0
   MINOR_IOV=999999
   
   # Function to query payloads
   query_payloads() {
       local gt_name=$1
       local major_iov=$2
       local minor_iov=$3
       
       curl -s "${BASE_URL}/payloadiovs/?gtName=${gt_name}&majorIOV=${major_iov}&minorIOV=${minor_iov}" | jq .
   }
   
   # Function to list global tags
   list_global_tags() {
       curl -s "${BASE_URL}/globalTags" | jq '.[].name'
   }
   
   # Usage
   echo "Global tags:"
   list_global_tags
   
   echo "Payloads for ${GT_NAME}:"
   query_payloads $GT_NAME $MAJOR_IOV $MINOR_IOV