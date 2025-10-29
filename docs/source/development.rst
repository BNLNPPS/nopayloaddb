.. _development:

Development Guide
=================

This guide covers development setup, testing, and contribution guidelines for the Nopayloaddb project.

Development Environment
------------------------

Prerequisites
~~~~~~~~~~~~~~

- Python 3.9 or higher
- PostgreSQL 12 or higher
- Git
- Docker and Docker Compose (for containerized development)

Local Development Setup
~~~~~~~~~~~~~~~~~~~~~~~~

**1. Clone and Setup**

.. code-block:: bash

   git clone https://github.com/BNLNPPS/nopayloaddb.git
   cd nopayloaddb
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt

**2. Database Setup**

Create PostgreSQL database and user:

.. code-block:: sql

   CREATE DATABASE nopayloaddb_dev;
   CREATE USER npdb_dev WITH PASSWORD 'dev_password';
   GRANT ALL PRIVILEGES ON DATABASE nopayloaddb_dev TO npdb_dev;

**3. Environment Configuration**

Create a ``.env`` file:

.. code-block:: bash

   export SECRET_KEY='your-development-secret-key-here'
   export DJANGO_LOGPATH='/tmp'
   
   # Database configuration
   export POSTGRES_DB_W=nopayloaddb_dev
   export POSTGRES_USER_W=npdb_dev
   export POSTGRES_PASSWORD_W=dev_password
   export POSTGRES_HOST_W=localhost
   export POSTGRES_PORT_W=5432
   
   # For read replicas (optional in development)
   export POSTGRES_DB_R1=nopayloaddb_dev
   export POSTGRES_USER_R1=npdb_dev
   export POSTGRES_PASSWORD_R1=dev_password
   export POSTGRES_HOST_R1=localhost
   export POSTGRES_PORT_R1=5432

**4. Run Migrations and Start Development Server**

.. code-block:: bash

   source .env
   python manage.py migrate
   python manage.py runserver

Docker Development Setup
~~~~~~~~~~~~~~~~~~~~~~~~~

For a more consistent development environment:

.. code-block:: bash

   git clone https://github.com/BNLNPPS/nopayloaddb.git
   cd nopayloaddb
   
   # Configure .env for Docker
   cat > .env << EOF
   SECRET_KEY='docker-dev-secret-key'
   DJANGO_LOGPATH='/npdb/logs'
   
   POSTGRES_DB_W=nopayloaddb
   POSTGRES_USER_W=npdb
   POSTGRES_PASSWORD_W=password
   POSTGRES_HOST_W=db
   POSTGRES_PORT_W=5432
   EOF
   
   # Start services
   docker-compose up --build

Local Kubernetes Development Setup
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This section covers local development using either **Minikube** (standard Kubernetes) or **OpenShift Local** (formerly CodeReady Containers). Choose the approach that matches your preferred platform.

**Prerequisites**

Choose one of the following setups:

**For Minikube (Standard Kubernetes):**

- Docker (for Minikube driver)
- Minikube installed
- kubectl installed
- Helm 3.x installed

**For OpenShift Local:**

- OpenShift Local (CRC) installed
- oc CLI tool installed  
- Helm 3.x installed

**1. Setup Local Kubernetes Environment**

**Option 1: Minikube Setup**

.. code-block:: bash

   # Start Minikube with Docker driver
   minikube start --driver=docker --cpus=4 --memory=8192

   # Enable required addons
   minikube addons enable ingress
   minikube addons enable dashboard
   minikube addons enable metrics-server

   # Verify cluster is running
   kubectl get nodes

   # Confirm the addons are enabled
   kubectl get namespaces
   kubectl get pods -n ingress-nginx

   # You can monitor the cluster using the dashboard:
   minikube dashboard --url

**Option 2: OpenShift Local Setup**

.. code-block:: bash

   # Start OpenShift Local (adjust memory/cpus as needed)
   crc start

   # Setup oc command line tool
   eval $(crc oc-env)

   # Login as developer (default credentials)
   oc login -u developer -p developer https://api.crc.testing:6443

   # Verify cluster is running
   oc get nodes

   # Check cluster status
   crc status

   # Access OpenShift console (optional)
   crc console --url


**2. Clone and Prepare Helm Charts**

.. code-block:: bash

   # Clone the charts repository (if not already done)
   git clone https://github.com/BNLNPPS/nopayloaddb-charts.git
   cd nopayloaddb-charts

**Important Note**: The original Helm charts are designed for OpenShift and use OpenShift-specific resources (``ImageStream`` and ``Route``). For **Minikube** users, these need to be modified. For **OpenShift Local** users, the original charts can be used as-is.

**2a. For Minikube Users: Create Kubernetes-Compatible Charts**

If using Minikube, modify the charts to work with standard Kubernetes:

.. code-block:: bash

   # Create a backup and modify the templates for Kubernetes compatibility
   cp -r nopayloaddb nopayloaddb-k8s
   cd nopayloaddb-k8s

   # Remove ImageStream from django.yaml (lines 1-15)
   sed -i '1,15d' templates/django.yaml

   # Remove ImageStream from pgbouncer.yaml (lines 1-15) 
   sed -i '1,15d' templates/pgbouncer.yaml

   # Remove OpenShift Route from nginx.yaml and replace with Kubernetes Ingress
   # First remove the Route section (lines 111-124)
   sed -i '111,124d' templates/nginx.yaml

   # Create Kubernetes Ingress for nginx
   cat >> templates/nginx.yaml << 'EOF'
   ---
   apiVersion: networking.k8s.io/v1
   kind: Ingress
   metadata:
     name: nginx-ingress
     labels:
       app: nginx
     annotations:
       nginx.ingress.kubernetes.io/rewrite-target: /
   spec:
     rules:
     - host: {{ .Values.appname }}.{{ .Values.domain }}
       http:
         paths:
         - path: /
           pathType: Prefix
           backend:
             service:
               name: nginx
               port:
                 number: 8080
   EOF

**2b. Create Custom Values Files**

Create the appropriate values file for your platform:

**For Minikube:**

.. code-block:: bash

   # Create custom values file for Minikube
   cat > nopayloaddb-k8s/values-minikube.yaml << EOF
   # Local Minikube configuration
   domain: minikube.local
   project: nopayloaddb-dev
   appname: nopayloaddb-dev
   
   # Database parameters (using local PostgreSQL)
   dbhost: postgresql
   dbname: nopayloaddb
   dbuser: npdb
   dbpassword: dev_password
   
   # Log paths
   django_logpath: /tmp/logs
   nginx_logpath: /tmp/logs
   pgbouncer_logpath: /tmp/logs
   
   # Persistent Volume Claims
   pvcname: nopayloaddb-pvc
   
   # Docker images (using public registry)
   # Note: ghcr.io/plexoos/npdb only supports x86_64/amd64 architecture
   # For ARM64 (Apple Silicon), see troubleshooting section for alternatives
   django_docker_image: ghcr.io/plexoos/npdb
   pgbouncer_docker_image: pgbouncer/pgbouncer
   django_docker_image_tag: latest
   pgbouncer_docker_image_tag: latest
   EOF

**For OpenShift Local:**

.. code-block:: bash

   # Create custom values file for OpenShift Local
   cat > nopayloaddb/values-openshift-local.yaml << EOF
   # OpenShift Local configuration
   domain: apps-crc.testing
   project: nopayloaddb-dev
   appname: nopayloaddb-dev
   
   # Database parameters (using local PostgreSQL)
   dbhost: postgresql
   dbname: nopayloaddb
   dbuser: npdb
   dbpassword: dev_password
   
   # Log paths
   django_logpath: /tmp/logs
   nginx_logpath: /tmp/logs
   pgbouncer_logpath: /tmp/logs
   
   # Persistent Volume Claims
   pvcname: nopayloaddb-pvc
   
   # Docker images (using public registry)
   # Note: ghcr.io/plexoos/npdb only supports x86_64/amd64 architecture
   # For ARM64 (Apple Silicon), see troubleshooting section for alternatives
   django_docker_image: ghcr.io/plexoos/npdb
   pgbouncer_docker_image: pgbouncer/pgbouncer
   django_docker_image_tag: latest
   pgbouncer_docker_image_tag: latest
   EOF

**3. Deploy PostgreSQL Database**

The database deployment is the same for both platforms:

.. code-block:: bash

   # Create namespace (use oc for OpenShift Local, kubectl for Minikube)
   # For Minikube:
   kubectl create namespace nopayloaddb-dev
   
   # For OpenShift Local:
   # oc new-project nopayloaddb-dev

   # Add Bitnami Helm repository for PostgreSQL
   helm repo add bitnami https://charts.bitnami.com/bitnami
   helm repo update

   # Deploy PostgreSQL (same command for both platforms)
   helm install postgresql bitnami/postgresql \
     --namespace nopayloaddb-dev \
     --set auth.postgresPassword=admin_password \
     --set auth.username=npdb \
     --set auth.password=dev_password \
     --set auth.database=nopayloaddb \
     --set persistence.enabled=true \
     --set persistence.size=10Gi

   # Wait for PostgreSQL to be ready (use kubectl for both platforms)
   kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=postgresql -n nopayloaddb-dev --timeout=300s

**4. Create Persistent Volume for Application**

.. code-block:: bash

   # Create PersistentVolumeClaim for application logs
   cat > nopayloaddb-pvc.yaml << EOF
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: nopayloaddb-pvc
     namespace: nopayloaddb-dev
   spec:
     accessModes:
       - ReadWriteOnce
     resources:
       requests:
         storage: 5Gi
   EOF

   kubectl apply -f nopayloaddb-pvc.yaml

**5. Deploy NoPayloadDB Application**

Choose the deployment method based on your platform:

**For Minikube:**

.. code-block:: bash

   # Install the application using the modified Kubernetes-compatible Helm chart
   helm install nopayloaddb ./nopayloaddb-k8s \
     --namespace nopayloaddb-dev \
     --values nopayloaddb-k8s/values-minikube.yaml

   # Wait for deployment to be ready
   kubectl wait --for=condition=available deployment/django -n nopayloaddb-dev --timeout=300s

   # Check pod status
   kubectl get pods -n nopayloaddb-dev

**For OpenShift Local:**

.. code-block:: bash

   # Install the application using the original OpenShift Helm chart
   helm install nopayloaddb ./nopayloaddb \
     --namespace nopayloaddb-dev \
     --values nopayloaddb/values-openshift-local.yaml

   # Wait for deployment to be ready
   kubectl wait --for=condition=available deployment/django -n nopayloaddb-dev --timeout=300s

   # Check pod status (you can use either oc or kubectl)
   oc get pods -n nopayloaddb-dev
   # or
   kubectl get pods -n nopayloaddb-dev

**6. Access the Application**

**For Minikube:**

.. code-block:: bash

   # Option 1: Port forward to access the application locally
   kubectl port-forward service/nginx 8080:8080 -n nopayloaddb-dev

   # Access the application at http://localhost:8080

   # Option 2: Use Minikube service (alternative method)
   minikube service nginx -n nopayloaddb-dev --url

   # Option 3: Use Ingress (if properly configured)
   # First get Minikube IP
   minikube ip
   # Then add to /etc/hosts: <minikube-ip> nopayloaddb-dev.minikube.local
   # Access via: http://nopayloaddb-dev.minikube.local

**For OpenShift Local:**

.. code-block:: bash

   # Option 1: Port forward to access the application locally
   oc port-forward service/nginx 8080:8080 -n nopayloaddb-dev

   # Access the application at http://localhost:8080

   # Option 2: Use OpenShift Route (automatically created)
   oc get routes -n nopayloaddb-dev
   # Access the application using the URL from the route

   # Option 3: Access via OpenShift console
   crc console
   # Navigate to the nopayloaddb-dev project to see the application

**7. Initialize Database Schema**

.. code-block:: bash

   # Run Django migrations
   kubectl exec -it deployment/django -n nopayloaddb-dev -- python manage.py migrate

   # Create Django superuser
   kubectl exec -it deployment/django -n nopayloaddb-dev -- python manage.py createsuperuser

   # Load initial data (if available)
   kubectl exec -it deployment/django -n nopayloaddb-dev -- python manage.py loaddata initial_data.json

**Development Workflow**

.. code-block:: bash

   # Check application logs
   kubectl logs -f deployment/django -n nopayloaddb-dev

   # Check PostgreSQL logs
   kubectl logs -f statefulset/postgresql -n nopayloaddb-dev

   # Access Django shell
   kubectl exec -it deployment/django -n nopayloaddb-dev -- python manage.py shell

   # Restart deployment after changes
   kubectl rollout restart deployment/django -n nopayloaddb-dev

   # Update application with Helm (choose based on your platform)
   
   # For Minikube:
   helm upgrade nopayloaddb ./nopayloaddb-k8s \
     --namespace nopayloaddb-dev \
     --values nopayloaddb-k8s/values-minikube.yaml
   
   # For OpenShift Local:
   helm upgrade nopayloaddb ./nopayloaddb \
     --namespace nopayloaddb-dev \
     --values nopayloaddb/values-openshift-local.yaml

**Cleanup**

**For Minikube:**

.. code-block:: bash

   # Remove the application
   helm uninstall nopayloaddb -n nopayloaddb-dev
   helm uninstall postgresql -n nopayloaddb-dev

   # Delete namespace
   kubectl delete namespace nopayloaddb-dev

   # Stop Minikube
   minikube stop

   # Delete Minikube cluster (optional - removes everything)
   minikube delete

**For OpenShift Local:**

.. code-block:: bash

   # Remove the application
   helm uninstall nopayloaddb -n nopayloaddb-dev
   helm uninstall postgresql -n nopayloaddb-dev

   # Delete project (namespace)
   oc delete project nopayloaddb-dev

   # Stop OpenShift Local
   crc stop

   # Delete OpenShift Local cluster (optional - removes everything)
   crc delete

**Troubleshooting**

**Platform-Specific Issues:**

- **Minikube - ImageStream/Route errors**: If you get errors about ``ImageStream`` or ``Route`` resources not found, you're trying to use the original OpenShift charts on standard Kubernetes. Follow the chart modification steps in section 2a above.

- **OpenShift Local - Standard Kubernetes resources not working**: If you're trying to use Kubernetes Ingress or other standard K8s resources on OpenShift Local, use the original OpenShift charts with Routes instead.

**Common Issues (Both Platforms):**

- **ImagePullBackOff on ARM64/Apple Silicon**: The default image ``ghcr.io/plexoos/npdb`` only supports x86_64/amd64 architecture. For ARM64 systems (Apple Silicon Macs), you have several options:

  **Option 1: Force x86_64 emulation in OpenShift Local**
  
  .. code-block:: bash
  
     # Stop current CRC instance
     crc stop
     crc delete
     
     # Start CRC with specific architecture emulation
     crc start --cpus 4 --memory 8192
     
     # The image should work with emulation, though performance may be slower

  **Option 2: Build your own ARM64 image**
  
  .. code-block:: bash
  
     # Clone the nopayloaddb repository
     git clone https://github.com/BNLNPPS/nopayloaddb.git
     cd nopayloaddb
     
     # Build for ARM64
     docker build --platform linux/arm64 -t nopayloaddb:arm64-local .
     
     # For OpenShift Local, import to the internal registry
     oc import-image nopayloaddb:arm64-local --from=nopayloaddb:arm64-local --confirm
     
     # Update values file to use your local image
     django_docker_image: image-registry.openshift-image-registry.svc:5000/nopayloaddb-dev/nopayloaddb
     django_docker_image_tag: arm64-local

  **Option 3: Use alternative deployment method**
  
  .. code-block:: bash
  
     # Deploy using standard Django/Python image and mount source code
     # This requires creating custom Kubernetes manifests instead of using Helm charts

- **Pod not starting**: Check ``kubectl describe pod <pod-name> -n nopayloaddb-dev``

- **Database connection issues**: Verify PostgreSQL is running and credentials are correct:
  
  .. code-block:: bash
  
     kubectl get pods -l app.kubernetes.io/name=postgresql -n nopayloaddb-dev
     kubectl logs -l app.kubernetes.io/name=postgresql -n nopayloaddb-dev

- **Image pull errors**: Ensure Minikube has access to the container registry:
  
  .. code-block:: bash
  
     # Check if images are being pulled
     kubectl describe pod <pod-name> -n nopayloaddb-dev
     
     # For private registries, you may need to configure image pull secrets

- **Storage issues**: Check PVC status with ``kubectl get pvc -n nopayloaddb-dev``

- **Nginx service not accessible**: Verify the service and port configuration:
  
  .. code-block:: bash
  
     kubectl get svc nginx -n nopayloaddb-dev
     kubectl get endpoints nginx -n nopayloaddb-dev

**Common OpenShift vs Kubernetes Issues**

The original Helm charts were designed for OpenShift and include resources that don't exist in standard Kubernetes:

- ``ImageStream`` (OpenShift) → Use standard Docker images directly in Kubernetes
- ``Route`` (OpenShift) → Replace with ``Ingress`` for Kubernetes  
- Different security contexts and user permissions

**Alternative: Direct Kubernetes Deployment (Without Helm Charts)**

If you prefer not to modify the Helm charts, you can deploy directly using standard Kubernetes manifests:

.. code-block:: bash

   # This approach bypasses the OpenShift-specific Helm charts entirely
   # and uses standard Kubernetes YAML files instead
   
   # Deploy PostgreSQL using Bitnami Helm chart (as shown in step 3)
   # Then create simple Kubernetes deployments for the Django app
   
   # Example Django deployment (create your own k8s manifests)
   kubectl create deployment django \
     --image=ghcr.io/plexoos/npdb:latest \
     --namespace=nopayloaddb-dev
   
   kubectl expose deployment django \
     --port=8000 \
     --namespace=nopayloaddb-dev
   
   # This method requires more manual configuration but avoids
   # OpenShift compatibility issues

**Accessing Platform Dashboards**

**For Minikube:**

.. code-block:: bash

   # Start the Kubernetes dashboard
   minikube dashboard

   # Or access via kubectl proxy
   kubectl proxy
   # Then visit: http://localhost:8001/api/v1/namespaces/kubernetes-dashboard/services/https:kubernetes-dashboard:/proxy/

**For OpenShift Local:**

.. code-block:: bash

   # Access OpenShift web console
   crc console

   # Or get the console URL
   crc console --url

   # Login with developer/developer or kubeadmin credentials
   # Developer user: developer / developer
   # Admin user credentials: 
   crc console --credentials

Code Structure
--------------

Project Layout
~~~~~~~~~~~~~~~

.. code-block:: text

   nopayloaddb/
   ├── nopayloaddb/          # Main Django project
   │   ├── __init__.py
   │   ├── settings.py       # Main settings
   │   ├── test_settings.py  # Test-specific settings
   │   ├── urls.py           # Main URL routing
   │   ├── wsgi.py           # WSGI application
   │   ├── db_router.py      # Database routing logic
   │   └── middleware.py     # Custom middleware
   ├── cdb_rest/             # Main application
   │   ├── __init__.py
   │   ├── models.py         # Database models
   │   ├── views.py          # API views
   │   ├── serializers.py    # DRF serializers
   │   ├── urls.py           # API URL routing
   │   ├── queries.py        # Custom queries
   │   ├── authentication.py # Auth logic
   │   └── migrations/       # Database migrations
   ├── docs/                 # Documentation
   ├── requirements.txt      # Python dependencies
   ├── manage.py            # Django management
   ├── Dockerfile           # Container definition
   └── docker-compose.yml   # Development services

Key Components
~~~~~~~~~~~~~~~

**Models (cdb_rest/models.py)**

- ``GlobalTag``: Named collections of payload versions
- ``GlobalTagStatus``: Status management for global tags
- ``PayloadType``: Categorization of payloads
- ``PayloadList``: Links global tags to payload types
- ``PayloadIOV``: Individual payloads with validity intervals

**Views (cdb_rest/views.py)**

- RESTful API endpoints using Django REST Framework
- Custom query views for complex IOV lookups
- Bulk operations for efficient data loading

**Database Router (nopayloaddb/db_router.py)**

- Handles read/write database splitting
- Currently routes all operations to default database
- Ready for read replica scaling

Testing
-------

Test Framework
~~~~~~~~~~~~~~~

The project uses Django's test framework with nose for enhanced testing capabilities.

**Running Tests**

.. code-block:: bash

   # Run all tests
   python manage.py test
   
   # Run specific test module
   python manage.py test cdb_rest.tests.test_models
   
   # Run with coverage
   python manage.py test --with-coverage --cover-package=cdb_rest

**Test Configuration**

Test settings are in ``nopayloaddb/test_settings.py``:

.. code-block:: python

   # Use nose for testing
   TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
   
   # Coverage configuration
   NOSE_ARGS = [
       '--with-coverage',
       '--cover-package=cdb_rest',
   ]

Writing Tests
~~~~~~~~~~~~~~

**Model Tests**

.. code-block:: python

   from django.test import TestCase
   from cdb_rest.models import GlobalTag, GlobalTagStatus
   
   class GlobalTagTestCase(TestCase):
       def setUp(self):
           self.status = GlobalTagStatus.objects.create(
               name='TEST',
               description='Test status'
           )
   
       def test_create_global_tag(self):
           gt = GlobalTag.objects.create(
               name='TestGT',
               author='testuser',
               description='Test global tag',
               status=self.status
           )
           self.assertEqual(gt.name, 'TestGT')
           self.assertEqual(str(gt), 'TestGT')

**API Tests**

.. code-block:: python

   from rest_framework.test import APITestCase
   from rest_framework import status
   
   class GlobalTagAPITestCase(APITestCase):
       def test_create_global_tag(self):
           url = '/api/cdb_rest/gt'
           data = {
               'name': 'TestGT',
               'author': 'testuser',
               'description': 'Test global tag',
               'status': 1
           }
           response = self.client.post(url, data, format='json')
           self.assertEqual(response.status_code, status.HTTP_201_CREATED)

Database Management
-------------------

Migrations
~~~~~~~~~~~

**Creating Migrations**

.. code-block:: bash

   # Create migration for model changes
   python manage.py makemigrations cdb_rest
   
   # Apply migrations
   python manage.py migrate
   
   # Check migration status
   python manage.py showmigrations

**Migration Best Practices**

- Always create migrations for model changes
- Review migration files before applying
- Test migrations on development data
- Use descriptive migration names

**Database Initialization**

.. code-block:: bash

   # Create superuser
   python manage.py createsuperuser
   
   # Load initial data (if fixtures exist)
   python manage.py loaddata initial_data.json

Performance Considerations
---------------------------

Database Optimization
~~~~~~~~~~~~~~~~~~~~~~

**Index Strategy**

The models include optimized indexes:

.. code-block:: python

   class PayloadIOV(models.Model):
       # ... fields ...
       
       class Meta:
           indexes = [
               models.Index('payload_list', F('comb_iov').desc(nulls_last=True), name='covering_idx')
           ]

**Query Optimization**

- Use ``select_related()`` for foreign key relationships
- Use ``prefetch_related()`` for reverse relationships
- Avoid N+1 queries in API endpoints

**Custom Queries**

Complex IOV queries use raw SQL for performance:

.. code-block:: python

   # In cdb_rest/queries.py
   def get_payloads_by_iov(gt_name, major_iov, minor_iov):
       cursor = connection.cursor()
       cursor.execute("""
           SELECT DISTINCT ... FROM PayloadIOV p
           JOIN PayloadList pl ON p.payload_list_id = pl.id
           WHERE pl.global_tag_id = %s AND ...
       """, [gt_name, major_iov, minor_iov])
       return cursor.fetchall()

Code Quality
-------------

Code Style
~~~~~~~~~~~

**PEP 8 Compliance**

- Use 4 spaces for indentation
- Line length limit of 79 characters
- Use descriptive variable names
- Follow Django naming conventions

**Import Organization**

.. code-block:: python

   # Standard library imports
   import os
   import sys
   
   # Third-party imports
   from django.db import models
   from rest_framework import serializers
   
   # Local imports
   from cdb_rest.models import GlobalTag

Documentation
~~~~~~~~~~~~~~

**Docstring Style**

.. code-block:: python

   def get_payloads_by_iov(gt_name, major_iov, minor_iov, payload_type=None):
       """
       Retrieve payloads for a specific global tag and IOV range.
       
       Args:
           gt_name (str): Name of the global tag
           major_iov (int): Major IOV value
           minor_iov (int): Minor IOV value
           payload_type (str, optional): Filter by payload type
       
       Returns:
           QuerySet: Filtered payload IOVs
       """
       pass

**API Documentation**

Use Django REST Framework's built-in documentation features:

.. code-block:: python

   class GlobalTagListCreateAPIView(ListCreateAPIView):
       """
       List all global tags or create a new global tag.
       
       GET: Returns a list of all global tags
       POST: Creates a new global tag
       """
       queryset = GlobalTag.objects.all()
       serializer_class = GlobalTagSerializer

Contributing
-------------

Git Workflow
~~~~~~~~~~~~~

**Branch Strategy**

- ``master``: Main development branch
- ``feature/feature-name``: Feature development
- ``bugfix/bug-description``: Bug fixes
- ``hotfix/urgent-fix``: Production hotfixes

**Commit Messages**

.. code-block:: text

   feat: add bulk payload IOV creation endpoint
   
   - Add new endpoint for bulk creation of payload IOVs
   - Improve performance for large data loads
   - Add validation for bulk operations
   
   Closes #123

**Pull Request Process**

1. Create feature branch from master
2. Make changes with appropriate tests
3. Ensure all tests pass
4. Update documentation if needed
5. Create pull request with description
6. Address code review feedback
7. Merge after approval

Code Review Guidelines
~~~~~~~~~~~~~~~~~~~~~~~

**Review Checklist**

- [ ] Code follows project style guidelines
- [ ] Tests are included and passing
- [ ] Documentation is updated
- [ ] No sensitive information in code
- [ ] Performance impact considered
- [ ] Security implications reviewed

**Common Issues to Check**

- SQL injection vulnerabilities
- Proper error handling
- Resource cleanup (database connections)
- Appropriate HTTP status codes
- Input validation

Development Tools
------------------

Useful Commands
~~~~~~~~~~~~~~~~

**Database Operations**

.. code-block:: bash

   # Reset database
   python manage.py flush
   
   # Dump data
   python manage.py dumpdata cdb_rest --indent=2 > data.json
   
   # Load data
   python manage.py loaddata data.json
   
   # Database shell
   python manage.py dbshell

**Development Server**

.. code-block:: bash

   # Run with debugging
   python manage.py runserver --verbosity=2
   
   # Run on specific port
   python manage.py runserver 0.0.0.0:9000

**Management Commands**

.. code-block:: bash

   # Django shell
   python manage.py shell
   
   # Create superuser
   python manage.py createsuperuser
   
   # Collect static files
   python manage.py collectstatic

IDE Configuration
~~~~~~~~~~~~~~~~~~

**VS Code Settings**

.. code-block:: json

   {
       "python.defaultInterpreterPath": "./venv/bin/python",
       "python.linting.enabled": true,
       "python.linting.pylintEnabled": false,
       "python.linting.flake8Enabled": true,
       "python.formatting.provider": "black",
       "python.testing.pytestEnabled": false,
       "python.testing.unittestEnabled": true,
       "python.testing.unittestArgs": [
           "-v",
           "-s",
           ".",
           "-p",
           "test_*.py"
       ]
   }

**PyCharm Configuration**

- Set Python interpreter to virtual environment
- Configure Django settings module: ``nopayloaddb.settings``
- Enable Django support in project settings
- Configure database connection for database tools

Debugging
----------

Common Issues
~~~~~~~~~~~~~

**Database Connection Issues**

.. code-block:: python

   # Check database connectivity
   from django.db import connection
   cursor = connection.cursor()
   cursor.execute("SELECT 1")
   print(cursor.fetchone())

**Migration Issues**

.. code-block:: bash

   # Check migration status
   python manage.py showmigrations
   
   # Fake migration (if needed)
   python manage.py migrate --fake cdb_rest 0001_initial

**Performance Issues**

.. code-block:: python

   # Enable SQL logging
   import logging
   logging.basicConfig()
   logging.getLogger('django.db.backends').setLevel(logging.DEBUG)

Debug Tools
~~~~~~~~~~~~

**Django Debug Toolbar**

Add to development requirements:

.. code-block:: python

   # In settings.py for development
   if DEBUG:
       INSTALLED_APPS.append('debug_toolbar')
       MIDDLEWARE.append('debug_toolbar.middleware.DebugToolbarMiddleware')
       INTERNAL_IPS = ['127.0.0.1']

**Django Extensions**

Useful for development:

.. code-block:: bash

   pip install django-extensions
   
   # Shell with IPython
   python manage.py shell_plus
   
   # Generate model graph
   python manage.py graph_models -a -g -o models.png