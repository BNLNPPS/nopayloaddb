.. _cdb_models:

====================
Database Models
====================

This section provides detailed documentation of the Django models that define the database schema for Nopayloaddb. These models represent the core entities in the conditions database system.

.. contents:: Table of Contents
   :local:
   :depth: 2

Overview
========

The Nopayloaddb data model is designed around five core entities that work together to provide a flexible and scalable conditions database system:

.. code-block:: text

   GlobalTagStatus ──┐
                    │
   GlobalTag ────────┴─── PayloadList ─── PayloadIOV
        │                      │
        └─── PayloadType ──────┘

Key Design Principles
=====================

**Metadata-Only Storage**
   The database stores references to payload files rather than the actual payload data, enabling efficient handling of large datasets.

**Flexible IOV Model** 
   Support for complex validity intervals using major/minor IOV pairs with optional end values.

**Read/Write Optimization**
   Database design supports read replica scaling and optimized query patterns.

**Version Management**
   Built-in support for payload versioning through Global Tags and Payload Lists.

Model Reference
===============

The following sections provide detailed information about each model, including fields, relationships, and usage patterns.

.. note::
   **Auto-Generated Documentation**: The detailed model documentation below is automatically generated from the Django model definitions and docstrings.

.. automodule:: cdb_rest.models
   :members:
   :undoc-members:
   :show-inheritance:

Model Relationships
===================

Understanding the relationships between models is crucial for effective use of the API:

Global Tag Hierarchy
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # A Global Tag can contain multiple Payload Lists
   global_tag = GlobalTag.objects.get(name="sPHENIX_Production_v1.0")
   payload_lists = global_tag.payloadlist_set.all()
   
   # Each Payload List is associated with one Payload Type
   for pl in payload_lists:
       print(f"List: {pl.name}, Type: {pl.payload_type.name}")

Payload IOV Access
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Access Payload IOVs through their Payload List
   payload_list = PayloadList.objects.get(name="Beam_Conditions_v1.0")
   iovs = payload_list.payloadiov_set.all()
   
   # Or query directly with filters
   recent_iovs = PayloadIOV.objects.filter(
       payload_list__global_tag__name="sPHENIX_Production_v1.0",
       major_iov__gte=1000
   ).order_by('-created')

Database Schema Details
=======================

Field Types and Constraints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Primary Keys**
   All models use auto-incrementing integer primary keys for optimal database performance.

**String Fields**
   - Names are typically limited to 200 characters with uniqueness constraints
   - Descriptions allow longer text (1000+ characters) for detailed information
   - URLs can accommodate long file paths and network locations

**Timestamp Fields**
   - All models include creation timestamps for audit trails
   - Timestamps use timezone-aware datetime objects
   - Automatic timestamp generation on record creation

**IOV Fields**
   - IOV values use BigInteger fields to support large run numbers
   - Combined IOV field (comb_iov) provides efficient indexing
   - Support for both point-in-time and range-based validity

Indexes and Performance
~~~~~~~~~~~~~~~~~~~~~~~

The models include several strategic indexes for query optimization:

**Covering Index**
   A composite index on (payload_list, comb_iov DESC NULLS LAST) optimizes the most common query pattern.

**Foreign Key Indexes**
   Automatic indexes on all foreign key relationships for efficient joins.

**Name Indexes**
   Unique indexes on name fields enable fast lookups by name.

Model Validation
================

Built-in Validation Rules
~~~~~~~~~~~~~~~~~~~~~~~~~

**Required Fields**
   - All models validate required fields at the Django level
   - Database-level NOT NULL constraints provide additional safety
   - Foreign key relationships are validated for referential integrity

**Custom Validation**
   - IOV ranges are validated to ensure start <= end
   - Name uniqueness is enforced within appropriate scopes
   - URL format validation for payload file references

**Data Integrity**
   - Cascade delete behavior protects against orphaned records
   - Transaction-level consistency for multi-model operations
   - Foreign key constraints maintain referential integrity

Common Query Patterns
======================

The following examples demonstrate common ways to query the models:

Finding Conditions for a Run
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from cdb_rest.models import PayloadIOV, PayloadList
   from django.db.models import Q
   
   def get_conditions_for_run(gt_name, run_number):
       """Get all payload IOVs valid for a specific run."""
       return PayloadIOV.objects.filter(
           payload_list__global_tag__name=gt_name,
           major_iov__lte=run_number,
           Q(major_iov_end__isnull=True) | Q(major_iov_end__gte=run_number)
       ).select_related('payload_list', 'payload_list__payload_type')

Creating New Conditions
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from cdb_rest.models import GlobalTag, PayloadType, PayloadList, PayloadIOV
   
   def create_calibration_set(gt_name, author, calibration_data):
       """Create a new set of calibration conditions."""
       
       # Create or get Global Tag
       gt, created = GlobalTag.objects.get_or_create(
           name=gt_name,
           defaults={
               'author': author,
               'description': f'Calibration set for {gt_name}',
               'status_id': 1
           }
       )
       
       # Create Payload Lists and IOVs
       for payload_type_name, iovs in calibration_data.items():
           payload_type = PayloadType.objects.get(name=payload_type_name)
           
           payload_list, created = PayloadList.objects.get_or_create(
               name=f"{payload_type_name}_{gt.id}",
               global_tag=gt,
               payload_type=payload_type
           )
           
           # Bulk create IOVs for efficiency
           iov_objects = [
               PayloadIOV(
                   payload_list=payload_list,
                   payload_url=iov['url'],
                   major_iov=iov['start_run'],
                   major_iov_end=iov['end_run'],
                   checksum=iov.get('checksum'),
                   size=iov.get('size')
               )
               for iov in iovs
           ]
           PayloadIOV.objects.bulk_create(iov_objects)

Model Extensions
================

Custom Manager Methods
~~~~~~~~~~~~~~~~~~~~~~

The models may include custom manager methods for common operations:

.. code-block:: python

   # Example: Custom manager for GlobalTag
   class GlobalTagManager(models.Manager):
       def active(self):
           """Return only active global tags."""
           return self.filter(status__name__in=['ACTIVE', 'PRODUCTION'])
       
       def for_experiment(self, experiment_name):
           """Filter global tags by experiment."""
           return self.filter(name__icontains=experiment_name)

Model Properties
~~~~~~~~~~~~~~~~

Models may include computed properties for convenience:

.. code-block:: python

   class PayloadIOV(models.Model):
       # ... field definitions ...
       
       @property
       def iov_range(self):
           """Return human-readable IOV range."""
           if self.major_iov_end:
               return f"{self.major_iov}-{self.major_iov_end}"
           return f"{self.major_iov}+"
       
       @property  
       def is_valid_for_run(self, run_number):
           """Check if this IOV is valid for a specific run."""
           if run_number < self.major_iov:
               return False
           if self.major_iov_end and run_number > self.major_iov_end:
               return False
           return True

Migration History
=================

Database Schema Evolution
~~~~~~~~~~~~~~~~~~~~~~~~~~

The models have evolved over time to support new features and optimize performance. Key schema changes include:

**Version 0.1**
   - Initial model definitions
   - Basic IOV support with single validity points
   - Simple foreign key relationships

**Version 0.2**
   - Added IOV range support (major_iov_end, minor_iov_end)
   - Introduced combined IOV field for indexing
   - Enhanced metadata fields (checksum, size)

**Version 0.3**
   - Performance optimizations with covering indexes
   - Added cascade delete behaviors
   - Enhanced validation rules

**Current Version**
   - Optimized query patterns
   - Full read/write splitting support
   - Production-ready constraints

Testing Models
==============

Unit Test Patterns
~~~~~~~~~~~~~~~~~~~

The models include comprehensive unit tests that demonstrate proper usage:

.. code-block:: python

   from django.test import TestCase
   from cdb_rest.models import GlobalTag, PayloadType, PayloadList, PayloadIOV
   
   class ModelTestCase(TestCase):
       def setUp(self):
           """Set up test data."""
           self.status = GlobalTagStatus.objects.create(
               name='TEST', description='Test status'
           )
           self.gt = GlobalTag.objects.create(
               name='TestGT', author='tester', 
               description='Test GT', status=self.status
           )
           self.pt = PayloadType.objects.create(
               name='TestType', description='Test payload type'
           )
   
       def test_payload_iov_creation(self):
           """Test creating payload IOVs."""
           pl = PayloadList.objects.create(
               name='TestList', global_tag=self.gt, payload_type=self.pt
           )
           
           iov = PayloadIOV.objects.create(
               payload_list=pl,
               payload_url='test_data.root',
               major_iov=1000,
               major_iov_end=2000
           )
           
           self.assertEqual(iov.iov_range, "1000-2000")
           self.assertTrue(iov.is_valid_for_run(1500))
           self.assertFalse(iov.is_valid_for_run(3000))

Best Practices
==============

Model Usage Guidelines
~~~~~~~~~~~~~~~~~~~~~~

**Efficient Querying**
   - Use select_related() for foreign key relationships
   - Use prefetch_related() for reverse relationships
   - Filter at the database level rather than in Python

**Bulk Operations**
   - Use bulk_create() for creating many records
   - Use bulk_update() for updating many records
   - Consider using raw SQL for complex operations

**Data Integrity**
   - Always use transactions for multi-model operations
   - Validate data before database operations
   - Handle constraint violations gracefully

**Performance Considerations**
   - Use appropriate indexes for query patterns
   - Consider denormalization for frequently accessed data
   - Monitor query performance and optimize as needed

See Also
========

- :doc:`api` - REST API endpoints for model operations
- :doc:`cdb_views` - Django views that handle model interactions
- :doc:`development` - Development guidelines and model testing
- :doc:`architecture` - Overall system architecture and design decisions