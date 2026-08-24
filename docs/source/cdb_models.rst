.. _cdb_models:

====================
Database Models
====================

The database schema is defined by five Django models in ``cdb_rest/models.py``:

.. mermaid::

   erDiagram
       GlobalTagStatus ||--o{ GlobalTag : "status"
       GlobalTag |o--o{ PayloadList : "payload_lists"
       PayloadType ||--o{ PayloadList : "payload_type"
       PayloadList |o--o{ PayloadIOV : "payload_iov"

       GlobalTagStatus {
           string name UK "unlocked / locked / frozen"
       }
       GlobalTag {
           string name UK
           string author
       }
       PayloadType {
           string name UK
       }
       PayloadList {
           string name UK "auto-generated: <type>_<id>"
       }
       PayloadIOV {
           string payload_url
           bigint major_iov
           bigint minor_iov
           bigint major_iov_end
           bigint minor_iov_end
           decimal comb_iov
       }

Design principles:

**Metadata-only storage**
   The database stores references (URLs) to payload files rather than the payload data
   itself.

**Flexible IOV model**
   Validity intervals use major/minor IOV pairs with optional end values; a combined
   decimal field (``comb_iov = major_iov + minor_iov / 10^19``) supports efficient
   "latest payload at a point" queries via the covering index
   ``(payload_list, comb_iov DESC NULLS LAST)``.

**Version management**
   Global Tags group payload lists into consistent, immutable-when-locked condition sets.

Model Reference
===============

The following documentation is generated from the model definitions.

.. automodule:: cdb_rest.models
   :members:
   :undoc-members:
   :show-inheritance:

Common Query Patterns
======================

Navigating the relationships from Python (the reverse relation names are
``payload_lists`` on ``GlobalTag`` and ``payload_iov`` on ``PayloadList``):

.. code-block:: python

   from cdb_rest.models import GlobalTag, PayloadList, PayloadIOV

   # Payload lists attached to a Global Tag, with their payload types
   gt = GlobalTag.objects.get(name="sPHENIX_ExampleGT_24")
   for pl in gt.payload_lists.all():
       print(pl.name, pl.payload_type.name)

   # Payload IOVs in a payload list
   pl = PayloadList.objects.get(name="Beam_210")
   iovs = pl.payload_iov.all()

   # Latest payload per list at a given IOV point, filtered by Global Tag
   from decimal import Decimal
   point = Decimal(major_iov) + Decimal(minor_iov) / 10**19
   latest = (PayloadIOV.objects
             .filter(payload_list__global_tag__name="sPHENIX_ExampleGT_24",
                     comb_iov__lte=point)
             .order_by('payload_list_id', '-comb_iov')
             .distinct('payload_list_id'))

Field notes:

- Name fields are unique and limited to 80 characters (255 for ``PayloadList``);
  description fields to 255 characters.
- IOV values are ``BigInteger`` to support large run numbers; open-ended IOVs use
  ``sys.maxsize``.
- All models carry auto-populated creation (and where relevant, update) timestamps.
- ``PayloadIOV.extra`` is a free-form field surfaced as ``revision`` by the
  ``/payloadiovs/`` query.

See Also
========

- :doc:`api` - REST API endpoints for model operations
- :doc:`cdb_views` - Django views that handle model interactions
- :doc:`architecture` - Overall system architecture and design decisions
