.. _cdb_views:

=================
Django Views
=================

The REST API is implemented with Django REST Framework class-based views in
``cdb_rest/views.py``. For endpoint URLs, parameters, and example requests, see
:doc:`api`; this page is the code-level reference.

View Categories
===============

**Global Tag views**
   List, retrieve (by ID or name), create, clone, delete, and change the status of Global
   Tags. Deletion and status changes enforce the ``locked``/``frozen`` immutability rules.

**Payload Type views**
   List, create, and delete payload types. Deletion is refused while any PayloadList still
   references the type.

**Payload List views**
   List and create payload lists (names are auto-generated from the payload type and a
   sequence ID), attach lists to Global Tags, and delete empty lists.

**Payload IOV views**
   Create payload IOVs (single or bulk), attach them to payload lists with
   overlap resolution, delete them, and query them. IOV validation and overlap handling
   delegate to the mode strategies in ``cdb_rest/iov_comparisons.py``
   (``CDB_IOV_MODE``).

**Query views**
   ``PayloadIOVsSQLListAPIView`` backs the main ``/payloadiovs/`` endpoint. It executes a
   raw SQL query from ``cdb_rest/queries.py`` (selected by the ``CDB_PAYLOAD_IOVS_QUERY``
   setting) and distributes reads across the configured ``read_db_*`` replicas.

**Settings view**
   ``CDBSettingAPIView`` exposes ``CDB_*`` environment variables read-only.

Authentication and Permissions
==============================

All views mix in ``WriteAuthMixin``: when ``CDB_AUTH_CLASS`` is set, write methods
(POST/PUT/PATCH/DELETE) authenticate with the configured class while reads stay anonymous.
Write views additionally call the permission plugin loaded from
``CDB_PERMISSION_PLUGIN_CLASS`` (see ``cdb_rest/permissions_plugins/``) before modifying
data.

View Reference
==============

The following documentation is generated from the view classes and their docstrings.

.. automodule:: cdb_rest.views
   :members:
   :undoc-members:
   :show-inheritance:

See Also
========

- :doc:`api` - Complete API endpoint documentation
- :doc:`cdb_models` - Database models used by these views
- :doc:`architecture` - Overall system architecture and design
