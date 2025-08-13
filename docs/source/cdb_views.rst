.. _cdb_views:

=================
Django Views
=================

This section provides detailed documentation of the Django views that implement the REST API endpoints for Nopayloaddb. These views handle HTTP requests and coordinate between the API layer and the database models.

.. contents:: Table of Contents
   :local:
   :depth: 2

Overview
========

The Nopayloaddb API is built using Django REST Framework (DRF) and follows RESTful design principles. The views are organized by resource type and provide full CRUD (Create, Read, Update, Delete) operations where appropriate.

**View Architecture**
   - **Class-based views** for consistent behavior and easy extension
   - **Django REST Framework** for serialization and HTTP handling
   - **Custom query optimization** for complex IOV lookups
   - **Bulk operation support** for performance-critical operations

Key Components
==============

**ViewSets and APIViews**
   Most endpoints are implemented as DRF ViewSets or APIViews for maximum flexibility.

**Custom Serializers**
   Specialized serializers handle the complex relationships between models.

**Query Optimization**
   Custom query methods use raw SQL for performance-critical operations.

**Error Handling**
   Consistent error responses with detailed information for debugging.

View Reference
==============

The following sections provide detailed information about each view, including supported HTTP methods, parameters, and response formats.

.. note::
   **Auto-Generated Documentation**: The detailed view documentation below is automatically generated from the Django view definitions and docstrings.

.. automodule:: cdb_rest.views
   :members:
   :undoc-members:
   :show-inheritance:

View Categories
===============

Global Tag Views
~~~~~~~~~~~~~~~~

These views handle operations on Global Tags, which represent named collections of payload versions.

**Supported Operations:**
- List all global tags
- Get specific global tag by name or ID
- Create new global tags
- Clone existing global tags  
- Update global tag status
- Delete global tags

**Key Features:**
- Automatic validation of global tag names
- Status management integration
- Cascade operations for related payload lists

Payload Type Views
~~~~~~~~~~~~~~~~~~

Views for managing payload type definitions, which categorize different kinds of conditions data.

**Supported Operations:**
- List all payload types
- Create new payload types
- Delete payload types (with safety checks)

**Key Features:**
- Uniqueness validation for payload type names
- Dependency checking before deletion
- Integration with payload list creation

Payload List Views
~~~~~~~~~~~~~~~~~~

These views manage payload lists, which link global tags to payload types and serve as containers for payload versions.

**Supported Operations:**
- List all payload lists
- Get payload lists for a specific global tag
- Create new payload lists
- Attach payload lists to global tags
- Delete payload lists

**Key Features:**
- Automatic relationship management
- Bulk operations for efficient data loading
- Validation of global tag and payload type relationships

Payload IOV Views
~~~~~~~~~~~~~~~~~

The most complex views handle payload IOVs (Intervals of Validity), which represent individual conditions data entries.

**Supported Operations:**
- Query payload IOVs by global tag and IOV range
- Create individual payload IOVs
- Bulk create multiple payload IOVs
- Attach payload IOVs to payload lists
- Delete payload IOVs (single or range)

**Key Features:**
- Optimized query methods for large datasets
- Complex IOV range validation
- Support for both ORM and raw SQL queries
- Bulk operation support for performance

Custom Query Methods
====================

The views include several optimized query methods for performance-critical operations:

Main Payload Query
~~~~~~~~~~~~~~~~~~

The primary endpoint for retrieving conditions data uses a custom SQL query for optimal performance:

.. code-block:: python

   def get_payloads_by_iov(gt_name, major_iov, minor_iov, payload_type=None):
       """
       Optimized query for payload IOVs using raw SQL.
       
       This method uses a carefully crafted SQL query with proper
       indexing to handle large datasets efficiently.
       """
       cursor = connection.cursor()
       
       base_query = """
           SELECT DISTINCT pl.id, pl.name, gt.name as gt_name,
                  pt.name as pt_name, piov.payload_url,
                  piov.major_iov, piov.minor_iov,
                  piov.created, piov.checksum, piov.size
           FROM "PayloadIOV" piov
           JOIN "PayloadList" pl ON piov.payload_list_id = pl.id
           JOIN "GlobalTag" gt ON pl.global_tag_id = gt.id
           JOIN "PayloadType" pt ON pl.payload_type_id = pt.id
           WHERE gt.name = %s AND piov.major_iov <= %s
       """
       
       params = [gt_name, major_iov]
       
       if payload_type:
           base_query += " AND pt.name = %s"
           params.append(payload_type)
           
       cursor.execute(base_query, params)
       return cursor.fetchall()

Alternative Query Endpoints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Additional query endpoints provide different optimization strategies:

**ORM-based Queries**
   For simpler operations where ORM convenience outweighs raw SQL performance.

**Aggregation Queries**
   Specialized endpoints for getting summary information like maximum IOV values.

**Filtered Queries**
   Pre-filtered endpoints for common query patterns.

Serializer Integration
======================

The views work closely with custom serializers to handle complex data transformations:

Nested Serialization
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   class PayloadListSerializer(serializers.ModelSerializer):
       """Serializer for PayloadList with nested IOV data."""
       
       payload_iov = PayloadIOVSerializer(many=True, read_only=True)
       global_tag = serializers.StringRelatedField()
       payload_type = serializers.StringRelatedField()
       
       class Meta:
           model = PayloadList
           fields = ['id', 'name', 'global_tag', 'payload_type', 
                    'payload_iov', 'created']

Dynamic Serialization
~~~~~~~~~~~~~~~~~~~~~~

Some views use dynamic serialization based on query parameters:

.. code-block:: python

   def get_serializer_class(self):
       """Return appropriate serializer based on request parameters."""
       if self.request.query_params.get('include_iovs'):
           return DetailedPayloadListSerializer
       return PayloadListSerializer

Validation and Error Handling
==============================

The views implement comprehensive validation and error handling:

Request Validation
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   def validate_iov_range(self, attrs):
       """Validate IOV range parameters."""
       major_start = attrs.get('major_iov')
       major_end = attrs.get('major_iov_end')
       
       if major_end and major_start > major_end:
           raise serializers.ValidationError(
               "IOV start must be less than or equal to IOV end"
           )
       
       return attrs

Error Response Format
~~~~~~~~~~~~~~~~~~~~~

Consistent error responses across all endpoints:

.. code-block:: python

   def handle_exception(self, exc):
       """Custom exception handler for consistent error responses."""
       
       if isinstance(exc, ValidationError):
           return Response({
               'error': 'Validation Error',
               'code': 400,
               'details': exc.detail,
               'timestamp': timezone.now().isoformat()
           }, status=400)
           
       return super().handle_exception(exc)

Performance Optimizations
=========================

The views include several performance optimizations:

Query Optimization
~~~~~~~~~~~~~~~~~~

**Select Related**
   Views use select_related() to minimize database queries:

.. code-block:: python

   def get_queryset(self):
       return PayloadIOV.objects.select_related(
           'payload_list',
           'payload_list__global_tag',
           'payload_list__payload_type'
       )

**Prefetch Related**
   For reverse relationships:

.. code-block:: python

   def get_queryset(self):
       return GlobalTag.objects.prefetch_related(
           'payloadlist_set__payloadiov_set'
       )

Caching Strategies
~~~~~~~~~~~~~~~~~~

**QuerySet Caching**
   Frequently accessed data is cached at the view level:

.. code-block:: python

   @cached_property
   def global_tags(self):
       """Cache global tag list for request duration."""
       return GlobalTag.objects.all().values('id', 'name')

**Response Caching**
   Static endpoints use HTTP caching headers:

.. code-block:: python

   @cache_control(max_age=3600)  # Cache for 1 hour
   def list(self, request):
       return super().list(request)

Bulk Operations
~~~~~~~~~~~~~~~

Specialized views handle bulk operations efficiently:

.. code-block:: python

   class BulkPayloadIOVCreateView(APIView):
       """Create multiple payload IOVs in a single transaction."""
       
       def post(self, request):
           with transaction.atomic():
               serializer = PayloadIOVSerializer(
                   data=request.data, many=True
               )
               if serializer.is_valid():
                   # Use bulk_create for performance
                   PayloadIOV.objects.bulk_create([
                       PayloadIOV(**item) for item in serializer.validated_data
                   ])
                   return Response({'created': len(request.data)}, 
                                 status=201)
               return Response(serializer.errors, status=400)

Authentication and Permissions
==============================

View-level security controls:

Authentication Classes
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   class SecurePayloadIOVViewSet(ModelViewSet):
       """Secured payload IOV operations."""
       
       authentication_classes = [
           TokenAuthentication,
           SessionAuthentication
       ]
       permission_classes = [IsAuthenticated]

Custom Permissions
~~~~~~~~~~~~~~~~~~

.. code-block:: python

   class IsOwnerOrReadOnly(BasePermission):
       """Allow owners to edit, others to read."""
       
       def has_object_permission(self, request, view, obj):
           if request.method in SAFE_METHODS:
               return True
           return obj.global_tag.author == request.user.username

Testing Views
=============

The views include comprehensive test coverage:

API Test Cases
~~~~~~~~~~~~~~

.. code-block:: python

   class PayloadIOVViewTestCase(APITestCase):
       """Test cases for payload IOV views."""
       
       def setUp(self):
           """Set up test data."""
           self.gt = GlobalTag.objects.create(
               name='TestGT', author='tester'
           )
           
       def test_create_payload_iov(self):
           """Test creating payload IOV via API."""
           url = '/api/cdb_rest/piov'
           data = {
               'payload_url': 'test_data.root',
               'major_iov': 1000,
               'payload_list': self.payload_list.id
           }
           response = self.client.post(url, data, format='json')
           self.assertEqual(response.status_code, 201)
           
       def test_query_payloads(self):
           """Test querying payloads by IOV."""
           url = '/api/cdb_rest/payloadiovs/'
           params = {
               'gtName': 'TestGT',
               'majorIOV': 1000,
               'minorIOV': 999999
           }
           response = self.client.get(url, params)
           self.assertEqual(response.status_code, 200)

Performance Testing
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   class PayloadIOVPerformanceTestCase(TestCase):
       """Performance tests for payload IOV operations."""
       
       @override_settings(DEBUG=True)
       def test_bulk_create_performance(self):
           """Test bulk creation performance."""
           
           # Create test data
           bulk_data = [
               {'payload_url': f'test_{i}.root', 'major_iov': i}
               for i in range(1000)
           ]
           
           with self.assertNumQueries(1):  # Should be single bulk query
               response = self.client.post(
                   '/api/cdb_rest/bulk_piov',
                   bulk_data,
                   format='json'
               )
               self.assertEqual(response.status_code, 201)

Documentation Integration
=========================

The views integrate with Django's built-in documentation features:

API Schema Generation
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   class PayloadIOVViewSet(ModelViewSet):
       """
       ViewSet for managing payload IOVs.
       
       Provides CRUD operations for payload intervals of validity,
       with support for complex queries by global tag and IOV range.
       """
       
       def list(self, request):
           """
           List payload IOVs with optional filtering.
           
           Query Parameters:
           - gtName: Global tag name (required)
           - majorIOV: Major IOV value (required) 
           - minorIOV: Minor IOV value (required)
           - payloadType: Filter by payload type (optional)
           """
           pass

Browsable API Integration
~~~~~~~~~~~~~~~~~~~~~~~~~

The views work seamlessly with DRF's browsable API for interactive exploration:

.. code-block:: python

   # settings.py
   REST_FRAMEWORK = {
       'DEFAULT_RENDERER_CLASSES': [
           'rest_framework.renderers.JSONRenderer',
           'rest_framework.renderers.BrowsableAPIRenderer',
       ],
   }

Custom View Mixins
==================

Reusable functionality through custom mixins:

IOV Query Mixin
~~~~~~~~~~~~~~~~

.. code-block:: python

   class IOVQueryMixin:
       """Mixin providing IOV query functionality."""
       
       def get_iov_filter(self, major_iov, minor_iov):
           """Build IOV filter conditions."""
           return Q(major_iov__lte=major_iov) & (
               Q(major_iov_end__isnull=True) |
               Q(major_iov_end__gte=major_iov)
           )
           
       def filter_by_iov(self, queryset, major_iov, minor_iov):
           """Apply IOV filtering to queryset."""
           return queryset.filter(
               self.get_iov_filter(major_iov, minor_iov)
           )

Bulk Operation Mixin
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   class BulkOperationMixin:
       """Mixin for bulk operations."""
       
       def bulk_create(self, request, *args, **kwargs):
           """Handle bulk creation requests."""
           serializer = self.get_serializer(data=request.data, many=True)
           if serializer.is_valid():
               with transaction.atomic():
                   instances = self.perform_bulk_create(serializer)
               return Response(
                   {'created': len(instances)}, 
                   status=status.HTTP_201_CREATED
               )
           return Response(serializer.errors, status=400)

Future Enhancements
===================

Planned improvements to the view layer:

**GraphQL Integration**
   Considering GraphQL endpoints for more flexible querying.

**WebSocket Support**
   Real-time updates for conditions data changes.

**Advanced Caching**
   Redis-based caching for high-performance scenarios.

**API Versioning**
   URL-based versioning for backward compatibility.

Best Practices
==============

Development Guidelines
~~~~~~~~~~~~~~~~~~~~~~

**View Design**
   - Keep views focused on HTTP handling
   - Move business logic to model methods or services
   - Use appropriate HTTP status codes
   - Provide detailed error messages

**Performance**
   - Profile database queries during development
   - Use appropriate serializer depth
   - Implement pagination for large datasets
   - Consider caching for read-heavy endpoints

**Testing**
   - Test all HTTP methods and status codes
   - Include edge cases and error conditions
   - Test authentication and permissions
   - Performance test bulk operations

**Documentation**
   - Include docstrings for all views
   - Document query parameters and response formats
   - Provide usage examples
   - Keep documentation synchronized with code

See Also
========

- :doc:`api` - Complete API endpoint documentation
- :doc:`cdb_models` - Database models used by these views  
- :doc:`development` - Development guidelines and testing
- :doc:`architecture` - Overall system architecture and design