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
           "payload_list": "Beam_210",
           "created": "2022-02-21T15:28:20.949696"
         }
       ],
       "created": "2022-02-21T15:17:06.481186"
     }
   ]

**Filter by Payload Type**

.. code-block:: bash

   curl 'http://localhost:8000/api/cdb_rest/payloadiovs/?gtName=sPHENIX_ExampleGT_24&payloadType=Beam&majorIOV=0&minorIOV=999999'

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

.. code-block:: bash

   curl -X POST http://localhost:8000/api/cdb_rest/gt \
     -H "Content-Type: application/json" \
     -d '{
       "name": "MyNewGT",
       "author": "username",
       "description": "New global tag for testing",
       "status": "Open"
     }'

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

.. code-block:: bash

   curl -X POST http://localhost:8000/api/cdb_rest/pl \
     -H "Content-Type: application/json" \
     -d '{
       "name": "MyPayloadList_123",
       "description": "Test payload list",
       "global_tag": 1,
       "payload_type": 1
     }'

**Attach Payload List to Global Tag**

.. code-block:: bash

   curl -X POST http://localhost:8000/api/cdb_rest/pl_attach \
     -H "Content-Type: application/json" \
     -d '{
       "global_tag": "MyGlobalTag",
       "payload_list": "MyPayloadList_123"
     }'

5. Managing Payload IOVs
~~~~~~~~~~~~~~~~~~~~~~~~~

**Create Single Payload IOV**

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
       "minor_iov_end": 2000,
       "payload_list": 1,
       "description": "Calibration data for run 1000-2000"
     }'

**Bulk Create Payload IOVs**

.. code-block:: bash

   curl -X POST http://localhost:8000/api/cdb_rest/bulk_piov \
     -H "Content-Type: application/json" \
     -d '[
       {
         "payload_url": "data1.root",
         "checksum": "sha256:1111...",
         "major_iov": 0,
         "minor_iov": 1000,
         "major_iov_end": 0,
         "minor_iov_end": 1500,
         "payload_list": 1
       },
       {
         "payload_url": "data2.root",
         "checksum": "sha256:2222...",
         "major_iov": 0,
         "minor_iov": 1500,
         "major_iov_end": 0,
         "minor_iov_end": 2000,
         "payload_list": 1
       }
     ]'

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

.. code-block:: json

   {
     "error": "Global tag not found",
     "code": 404,
     "details": "Global tag 'NonExistentGT' does not exist"
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

- Verify that authentication is properly configured if enabled
- Check that valid tokens are being sent in requests

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
       
       def get_payloads(self, gt_name, major_iov, minor_iov, payload_type=None):
           """Get payloads for a specific global tag and IOV."""
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
       
       def create_global_tag(self, name, author, description, status_id):
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