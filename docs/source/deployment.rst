.. _deployment:

Deployment Guide
================

This guide covers production deployment options for the Nopayloaddb service.

Production Considerations
--------------------------

Security Requirements
~~~~~~~~~~~~~~~~~~~~~~

**Environment Variables**

Never use default values in production:

.. code-block:: bash

   # Required production settings
   export SECRET_KEY='your-very-secure-secret-key-here'
   export DEBUG=False
   export DJANGO_LOGPATH='/var/log/nopayloaddb'
   
   # Database credentials
   export POSTGRES_DB_W=nopayloaddb_prod
   export POSTGRES_USER_W=npdb_prod
   export POSTGRES_PASSWORD_W='secure-password'
   export POSTGRES_HOST_W=db.example.com
   export POSTGRES_PORT_W=5432

**Django Settings**

Ensure production settings in ``nopayloaddb/settings.py``:

.. code-block:: python

   # Security settings
   DEBUG = False
   ALLOWED_HOSTS = ['your-domain.com', 'api.example.com']
   
   # Use secure cookies
   SESSION_COOKIE_SECURE = True
   CSRF_COOKIE_SECURE = True
   
   # Enable authentication if required
   REST_FRAMEWORK = {
       'DEFAULT_AUTHENTICATION_CLASSES': [
           'rest_framework.authentication.TokenAuthentication',
       ],
       'DEFAULT_PERMISSION_CLASSES': [
           'rest_framework.permissions.IsAuthenticated',
       ],
   }

**HTTPS/TLS Configuration**

Always use HTTPS in production:

- Configure SSL/TLS certificates
- Use secure headers
- Implement proper certificate management

Container Deployment
---------------------

Docker Production Setup
~~~~~~~~~~~~~~~~~~~~~~~~

**Production Dockerfile**

.. code-block:: dockerfile

   FROM python:3.9.16-slim
   
   # Security updates
   RUN apt-get update && apt-get upgrade -y && \
       apt-get install -y --no-install-recommends \
       libpq-dev gcc && \
       rm -rf /var/lib/apt/lists/*
   
   # Create non-root user
   RUN groupadd -r npdb && useradd -r -g npdb npdb
   
   WORKDIR /app
   
   # Install dependencies
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   # Copy application
   COPY . .
   RUN chown -R npdb:npdb /app
   
   USER npdb
   
   # Production command
   CMD ["gunicorn", "--bind", "0.0.0.0:8000", "nopayloaddb.wsgi:application"]

**Production Docker Compose**

.. code-block:: yaml

   version: '3.8'
   
   services:
     db:
       image: postgres:13
       environment:
         - POSTGRES_DB=${POSTGRES_DB_W}
         - POSTGRES_USER=${POSTGRES_USER_W}
         - POSTGRES_PASSWORD=${POSTGRES_PASSWORD_W}
       volumes:
         - postgres_data:/var/lib/postgresql/data
         - ./backup:/backup
       restart: unless-stopped
       healthcheck:
         test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER_W}"]
         interval: 10s
         timeout: 5s
         retries: 5
   
     app:
       build:
         context: .
         dockerfile: Dockerfile.prod
       depends_on:
         db:
           condition: service_healthy
       environment:
         - SECRET_KEY=${SECRET_KEY}
         - DEBUG=False
         - POSTGRES_HOST_W=db
       volumes:
         - static_files:/app/static
         - media_files:/app/media
         - logs:/var/log/nopayloaddb
       restart: unless-stopped
       healthcheck:
         test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
         interval: 30s
         timeout: 10s
         retries: 3
   
     nginx:
       image: nginx:alpine
       depends_on:
         - app
       ports:
         - "80:80"
         - "443:443"
       volumes:
         - ./nginx.conf:/etc/nginx/nginx.conf
         - static_files:/static
         - ./ssl:/etc/nginx/ssl
       restart: unless-stopped
   
   volumes:
     postgres_data:
     static_files:
     media_files:
     logs:

Kubernetes Deployment
~~~~~~~~~~~~~~~~~~~~~~

**Namespace and ConfigMap**

.. code-block:: yaml

   apiVersion: v1
   kind: Namespace
   metadata:
     name: nopayloaddb
   
   ---
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: nopayloaddb-config
     namespace: nopayloaddb
   data:
     DEBUG: "False"
     DJANGO_LOGPATH: "/var/log/nopayloaddb"
     POSTGRES_HOST_W: "postgresql"
     POSTGRES_PORT_W: "5432"
     POSTGRES_DB_W: "nopayloaddb"

**Secrets**

.. code-block:: yaml

   apiVersion: v1
   kind: Secret
   metadata:
     name: nopayloaddb-secrets
     namespace: nopayloaddb
   type: Opaque
   data:
     SECRET_KEY: <base64-encoded-secret>
     POSTGRES_USER_W: <base64-encoded-username>
     POSTGRES_PASSWORD_W: <base64-encoded-password>

**Deployment**

.. code-block:: yaml

   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: nopayloaddb
     namespace: nopayloaddb
   spec:
     replicas: 3
     selector:
       matchLabels:
         app: nopayloaddb
     template:
       metadata:
         labels:
           app: nopayloaddb
       spec:
         containers:
         - name: nopayloaddb
           image: nopayloaddb:latest
           ports:
           - containerPort: 8000
           envFrom:
           - configMapRef:
               name: nopayloaddb-config
           - secretRef:
               name: nopayloaddb-secrets
           resources:
             requests:
               cpu: 100m
               memory: 256Mi
             limits:
               cpu: 500m
               memory: 512Mi
           livenessProbe:
             httpGet:
               path: /health/
               port: 8000
             initialDelaySeconds: 30
             periodSeconds: 10
           readinessProbe:
             httpGet:
               path: /ready/
               port: 8000
             initialDelaySeconds: 5
             periodSeconds: 5

**Service and Ingress**

.. code-block:: yaml

   apiVersion: v1
   kind: Service
   metadata:
     name: nopayloaddb-service
     namespace: nopayloaddb
   spec:
     selector:
       app: nopayloaddb
     ports:
     - port: 80
       targetPort: 8000
     type: ClusterIP
   
   ---
   apiVersion: networking.k8s.io/v1
   kind: Ingress
   metadata:
     name: nopayloaddb-ingress
     namespace: nopayloaddb
     annotations:
       nginx.ingress.kubernetes.io/rewrite-target: /
       cert-manager.io/cluster-issuer: letsencrypt-prod
   spec:
     tls:
     - hosts:
       - api.example.com
       secretName: nopayloaddb-tls
     rules:
     - host: api.example.com
       http:
         paths:
         - path: /
           pathType: Prefix
           backend:
             service:
               name: nopayloaddb-service
               port:
                 number: 80

Helm Charts Deployment
~~~~~~~~~~~~~~~~~~~~~~~

.. note::
   **Official Helm Charts**: Nopayloaddb provides official Helm charts for production deployments on Kubernetes and OpenShift clusters. These charts are actively maintained and include configurations for different HEP experiments.

**Repository**: https://github.com/BNLNPPS/nopayloaddb-charts

The Helm charts repository provides pre-configured deployment templates for:

- **sPHENIX experiment**: ``npdbchart_sphenix/``
- **Belle2 Java backend**: ``npdbchart_belle2_java/``

**Quick Start with Helm Charts**

.. code-block:: bash

   # Clone the charts repository
   git clone https://github.com/BNLNPPS/nopayloaddb-charts.git
   cd nopayloaddb-charts

**For sPHENIX Deployment:**

.. code-block:: bash

   # Copy your configuration values
   cp /path/to/your/values_sphenix.yaml npdbchart_sphenix/values.yaml
   
   # Login to your cluster
   oc login --token='YOUR_TOKEN'
   oc project your-project-name
   
   # Deploy or upgrade
   helm upgrade --install sphenix-npdb npdbchart_sphenix/
   
   # Check deployment status
   oc get pods
   helm list

**For Belle2 Java Deployment:**

.. code-block:: bash

   # Copy your configuration values
   cp /path/to/your/values_belle2-java.yaml npdbchart_belle2_java/values.yaml
   
   # Deploy or upgrade
   helm upgrade --install belle2-npdb npdbchart_belle2_java/

**Helm Chart Configuration**

The Helm charts support comprehensive configuration through ``values.yaml``:

.. code-block:: yaml

   # Example values.yaml structure
   image:
     repository: ghcr.io/plexoos/npdb
     tag: latest
     pullPolicy: Always
   
   service:
     type: ClusterIP
     port: 8000
   
   ingress:
     enabled: true
     annotations:
       kubernetes.io/ingress.class: nginx
     hosts:
       - host: npdb.example.com
         paths:
           - path: /
             pathType: Prefix
   
   postgresql:
     enabled: true
     auth:
       postgresPassword: "secure-password"
       database: nopayloaddb
   
   resources:
     limits:
       cpu: 500m
       memory: 512Mi
     requests:
       cpu: 100m
       memory: 256Mi

**Monitoring and Troubleshooting with Helm**

.. code-block:: bash

   # Monitor deployment
   helm status your-release-name
   
   # Get deployment logs
   oc logs deployment/nopayloaddb
   
   # Debug issues
   oc describe pod <pod-name>
   oc get events --sort-by='.metadata.creationTimestamp'
   
   # Restart deployment (delete pod to force restart)
   oc delete pod <pod-name>

**Advantages of Helm Charts**

- **Production-Ready**: Pre-configured with best practices
- **Experiment-Specific**: Tailored configurations for different HEP experiments  
- **Version Management**: Easy rollbacks and upgrades
- **Configuration Management**: Centralized values management
- **Integration**: Seamless OpenShift/Kubernetes integration

OpenShift Deployment
~~~~~~~~~~~~~~~~~~~~~

**Using the Provided Template**

.. code-block:: bash

   # Login to OpenShift
   oc login https://your-openshift-cluster.com
   
   # Create or select project
   oc new-project nopayloaddb-prod
   
   # Create template
   oc create -f npdb_openshift_template.yaml
   
   # Deploy application
   oc new-app --template=npdb \
     -p DATABASE_SERVICE_NAME=postgresql \
     -p DATABASE_NAME=nopayloaddb \
     -p DATABASE_USER=npdb \
     -p DATABASE_PASSWORD=secure-password \
     -p SECRET_KEY=your-secure-secret-key

**Custom OpenShift Configuration**

.. code-block:: yaml

   apiVersion: template.openshift.io/v1
   kind: Template
   metadata:
     name: nopayloaddb-template
   objects:
   - apiVersion: apps/v1
     kind: Deployment
     metadata:
       name: nopayloaddb
     spec:
       replicas: 2
       selector:
         matchLabels:
           app: nopayloaddb
       template:
         metadata:
           labels:
             app: nopayloaddb
         spec:
           containers:
           - name: nopayloaddb
             image: ghcr.io/plexoos/npdb:latest
             env:
             - name: SECRET_KEY
               valueFrom:
                 secretKeyRef:
                   name: nopayloaddb-secrets
                   key: secret-key
             - name: POSTGRES_HOST_W
               value: postgresql
             ports:
             - containerPort: 8000
   parameters:
   - name: SECRET_KEY
     description: Django secret key
     required: true
   - name: DATABASE_PASSWORD
     description: Database password
     required: true

Traditional Deployment
-----------------------

WSGI Server Setup
~~~~~~~~~~~~~~~~~~

**Using Gunicorn**

.. code-block:: bash

   # Install Gunicorn
   pip install gunicorn
   
   # Create Gunicorn configuration
   cat > gunicorn.conf.py << 'EOF'
   bind = "0.0.0.0:8000"
   workers = 4
   worker_class = "sync"
   worker_connections = 1000
   max_requests = 1000
   max_requests_jitter = 50
   timeout = 30
   keepalive = 2
   user = "npdb"
   group = "npdb"
   preload_app = True
   
   # Logging
   accesslog = "/var/log/nopayloaddb/access.log"
   errorlog = "/var/log/nopayloaddb/error.log"
   loglevel = "info"
   
   # Process naming
   proc_name = "nopayloaddb"
   
   # Worker recycling
   max_requests = 1000
   max_requests_jitter = 50
   EOF
   
   # Start Gunicorn
   gunicorn --config gunicorn.conf.py nopayloaddb.wsgi:application

**Using uWSGI**

.. code-block:: bash

   # Install uWSGI
   pip install uwsgi
   
   # Create uWSGI configuration
   cat > uwsgi.ini << 'EOF'
   [uwsgi]
   module = nopayloaddb.wsgi:application
   master = true
   processes = 4
   socket = /tmp/uwsgi.sock
   chmod-socket = 666
   vacuum = true
   die-on-term = true
   logto = /var/log/nopayloaddb/uwsgi.log
   EOF
   
   # Start uWSGI
   uwsgi --ini uwsgi.ini

Reverse Proxy Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Nginx Configuration**

.. code-block:: nginx

   upstream nopayloaddb {
       server 127.0.0.1:8000;
       # Add more servers for load balancing
       # server 127.0.0.1:8001;
   }
   
   server {
       listen 80;
       server_name api.example.com;
       return 301 https://$server_name$request_uri;
   }
   
   server {
       listen 443 ssl http2;
       server_name api.example.com;
   
       ssl_certificate /etc/ssl/certs/api.example.com.crt;
       ssl_certificate_key /etc/ssl/private/api.example.com.key;
   
       # Security headers
       add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
       add_header X-Frame-Options DENY always;
       add_header X-Content-Type-Options nosniff always;
       add_header X-XSS-Protection "1; mode=block" always;
   
       # Client max body size
       client_max_body_size 10M;
   
       # Compression
       gzip on;
       gzip_vary on;
       gzip_types
           text/plain
           text/css
           text/xml
           text/javascript
           application/javascript
           application/xml+rss
           application/json;
   
       location / {
           proxy_pass http://nopayloaddb;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
           
           # Timeouts
           proxy_connect_timeout 30s;
           proxy_send_timeout 30s;
           proxy_read_timeout 30s;
       }
   
       location /static/ {
           alias /var/www/nopayloaddb/static/;
           expires 1y;
           add_header Cache-Control "public, immutable";
       }
   
       location /health/ {
           access_log off;
           proxy_pass http://nopayloaddb;
       }
   }

**Apache Configuration**

.. code-block:: apache

   <VirtualHost *:80>
       ServerName api.example.com
       Redirect permanent / https://api.example.com/
   </VirtualHost>
   
   <VirtualHost *:443>
       ServerName api.example.com
       
       SSLEngine on
       SSLCertificateFile /etc/ssl/certs/api.example.com.crt
       SSLCertificateKeyFile /etc/ssl/private/api.example.com.key
       
       # Security headers
       Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"
       Header always set X-Frame-Options DENY
       Header always set X-Content-Type-Options nosniff
       
       # Proxy configuration
       ProxyPreserveHost On
       ProxyRequests Off
       
       ProxyPass /static/ !
       ProxyPass / http://127.0.0.1:8000/
       ProxyPassReverse / http://127.0.0.1:8000/
       
       # Static files
       Alias /static /var/www/nopayloaddb/static
       <Directory /var/www/nopayloaddb/static>
           Require all granted
       </Directory>
   </VirtualHost>

Database Setup
---------------

PostgreSQL Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~

**Production Database Setup**

.. code-block:: psql

   -- Create production database
   CREATE DATABASE nopayloaddb_prod;
   
   -- Create users
   CREATE USER npdb_write WITH PASSWORD 'secure-write-password';
   CREATE USER npdb_read WITH PASSWORD 'secure-read-password';
   
   -- Grant permissions
   GRANT ALL PRIVILEGES ON DATABASE nopayloaddb_prod TO npdb_write;
   GRANT CONNECT ON DATABASE nopayloaddb_prod TO npdb_read;
   
   -- Connect to database
   \\c nopayloaddb_prod
   
   -- Grant schema permissions
   GRANT USAGE ON SCHEMA public TO npdb_read;
   GRANT SELECT ON ALL TABLES IN SCHEMA public TO npdb_read;
   GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO npdb_read;
   
   -- Set default privileges
   ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO npdb_read;

**Database Optimization**

.. code-block:: sql

   -- Analyze tables for query optimization
   ANALYZE;
   
   -- Create additional indexes if needed
   CREATE INDEX idx_payloadiov_major_minor ON "PayloadIOV" (major_iov, minor_iov);
   CREATE INDEX idx_payloadlist_gt_type ON "PayloadList" (global_tag_id, payload_type_id);
   
   -- Vacuum and analyze regularly
   VACUUM ANALYZE;

**Read Replicas Configuration**

.. code-block:: bash

   # On primary server
   echo "wal_level = replica" >> /etc/postgresql/13/main/postgresql.conf
   echo "max_wal_senders = 3" >> /etc/postgresql/13/main/postgresql.conf
   echo "wal_keep_segments = 64" >> /etc/postgresql/13/main/postgresql.conf
   
   # Add replica user
   echo "host replication replica_user replica_ip/32 md5" >> /etc/postgresql/13/main/pg_hba.conf
   
   # Restart PostgreSQL
   systemctl restart postgresql

Monitoring and Logging
-----------------------

Application Monitoring
~~~~~~~~~~~~~~~~~~~~~~~

**Health Check Endpoint**

.. code-block:: python

   # Add to urls.py
   from django.http import JsonResponse
   from django.db import connection
   
   def health_check(request):
       try:
           cursor = connection.cursor()
           cursor.execute("SELECT 1")
           return JsonResponse({
               'status': 'healthy',
               'database': 'connected',
               'timestamp': timezone.now().isoformat()
           })
       except Exception as e:
           return JsonResponse({
               'status': 'unhealthy',
               'error': str(e),
               'timestamp': timezone.now().isoformat()
           }, status=500)

**Prometheus Metrics**

.. code-block:: bash

   # Install django-prometheus
   pip install django-prometheus
   
   # Add to INSTALLED_APPS
   INSTALLED_APPS = [
       'django_prometheus',
       # ... other apps
   ]
   
   # Add to MIDDLEWARE
   MIDDLEWARE = [
       'django_prometheus.middleware.PrometheusBeforeMiddleware',
       # ... other middleware
       'django_prometheus.middleware.PrometheusAfterMiddleware',
   ]

**Logging Configuration**

.. code-block:: python

   # Production logging settings
   LOGGING = {
       'version': 1,
       'disable_existing_loggers': False,
       'formatters': {
           'verbose': {
               'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
               'style': '{',
           },
           'simple': {
               'format': '{levelname} {message}',
               'style': '{',
           },
       },
       'handlers': {
           'file': {
               'level': 'INFO',
               'class': 'logging.handlers.RotatingFileHandler',
               'filename': '/var/log/nopayloaddb/django.log',
               'maxBytes': 1024*1024*50,  # 50MB
               'backupCount': 5,
               'formatter': 'verbose',
           },
           'console': {
               'level': 'INFO',
               'class': 'logging.StreamHandler',
               'formatter': 'simple',
           },
       },
       'loggers': {
           'django': {
               'handlers': ['file', 'console'],
               'level': 'INFO',
               'propagate': True,
           },
           'cdb_rest': {
               'handlers': ['file', 'console'],
               'level': 'INFO',
               'propagate': True,
           },
       },
   }

Database Monitoring
~~~~~~~~~~~~~~~~~~~~

**PostgreSQL Monitoring**

.. code-block:: sql

   -- Monitor active connections
   SELECT count(*) FROM pg_stat_activity;
   
   -- Monitor query performance
   SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;
   
   -- Monitor database size
   SELECT pg_size_pretty(pg_database_size('nopayloaddb_prod'));
   
   -- Monitor table sizes
   SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
   FROM pg_tables WHERE schemaname = 'public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

Backup and Recovery
--------------------

Database Backups
~~~~~~~~~~~~~~~~~

**Automated Backup Script**

.. code-block:: bash

   #!/bin/bash
   
   # Configuration
   DB_NAME="nopayloaddb_prod"
   DB_USER="npdb_write"
   BACKUP_DIR="/backup/nopayloaddb"
   DATE=$(date +%Y%m%d_%H%M%S)
   
   # Create backup directory
   mkdir -p $BACKUP_DIR
   
   # Create database backup
   pg_dump -h localhost -U $DB_USER -d $DB_NAME -f "$BACKUP_DIR/nopayloaddb_$DATE.sql"
   
   # Compress backup
   gzip "$BACKUP_DIR/nopayloaddb_$DATE.sql"
   
   # Remove old backups (keep last 7 days)
   find $BACKUP_DIR -name "*.gz" -mtime +7 -delete
   
   # Verify backup
   if [ -f "$BACKUP_DIR/nopayloaddb_$DATE.sql.gz" ]; then
       echo "Backup successful: nopayloaddb_$DATE.sql.gz"
   else
       echo "Backup failed"
       exit 1
   fi

**Cron Job for Automated Backups**

.. code-block:: bash

   # Add to crontab
   0 2 * * * /usr/local/bin/backup_nopayloaddb.sh

**Backup Verification**

.. code-block:: bash

   #!/bin/bash
   
   # Test backup restoration
   gunzip -c /backup/nopayloaddb/nopayloaddb_latest.sql.gz | psql -h localhost -U npdb_write -d nopayloaddb_test

Disaster Recovery
~~~~~~~~~~~~~~~~~~

**Recovery Procedure**

.. code-block:: bash

   # 1. Stop application
   systemctl stop nopayloaddb
   
   # 2. Restore database
   createdb nopayloaddb_prod_restored
   gunzip -c /backup/nopayloaddb/nopayloaddb_YYYYMMDD.sql.gz | psql -h localhost -U npdb_write -d nopayloaddb_prod_restored
   
   # 3. Verify data integrity
   psql -h localhost -U npdb_write -d nopayloaddb_prod_restored -c "SELECT COUNT(*) FROM \"GlobalTag\";"
   
   # 4. Update configuration to use restored database
   # 5. Start application
   systemctl start nopayloaddb

**High Availability Setup**

.. code-block:: bash

   # Configure PostgreSQL streaming replication
   # Primary server configuration
   echo "hot_standby = on" >> /etc/postgresql/13/main/postgresql.conf
   echo "wal_level = replica" >> /etc/postgresql/13/main/postgresql.conf
   echo "max_wal_senders = 3" >> /etc/postgresql/13/main/postgresql.conf
   
   # Standby server configuration
   echo "hot_standby = on" >> /etc/postgresql/13/main/postgresql.conf
   echo "primary_conninfo = 'host=primary_server port=5432 user=replication'" >> /etc/postgresql/13/main/recovery.conf

Performance Optimization
-------------------------

Application Performance
~~~~~~~~~~~~~~~~~~~~~~~~

**Django Optimization**

.. code-block:: python

   # settings.py optimizations
   
   # Database connection pooling
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'OPTIONS': {
               'MAX_CONNS': 20,
               'MIN_CONNS': 5,
           },
       }
   }
   
   # Caching
   CACHES = {
       'default': {
           'BACKEND': 'django.core.cache.backends.redis.RedisCache',
           'LOCATION': 'redis://127.0.0.1:6379/1',
       }
   }
   
   # Session optimization
   SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
   SESSION_CACHE_ALIAS = 'default'

**Load Balancing**

.. code-block:: nginx

   upstream nopayloaddb {
       least_conn;
       server 127.0.0.1:8000 weight=3;
       server 127.0.0.1:8001 weight=2;
       server 127.0.0.1:8002 weight=1;
   }

Security Hardening
-------------------

System Security
~~~~~~~~~~~~~~~~

**Firewall Configuration**

.. code-block:: bash

   # Allow only necessary ports
   ufw allow 22/tcp   # SSH
   ufw allow 80/tcp   # HTTP
   ufw allow 443/tcp  # HTTPS
   ufw allow 5432/tcp from 10.0.0.0/8  # PostgreSQL (internal only)
   ufw enable

**SSL/TLS Configuration**

.. code-block:: nginx

   # Strong SSL configuration
   ssl_protocols TLSv1.2 TLSv1.3;
   ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
   ssl_prefer_server_ciphers off;
   ssl_dhparam /etc/nginx/dhparam.pem;
   
   # OCSP stapling
   ssl_stapling on;
   ssl_stapling_verify on;

**Regular Security Updates**

.. code-block:: bash

   # Automated security updates
   echo 'Unattended-Upgrade::Allowed-Origins {
       "${distro_id}:${distro_codename}-security";
   };' > /etc/apt/apt.conf.d/50unattended-upgrades
   
   systemctl enable unattended-upgrades