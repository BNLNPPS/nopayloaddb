.. _kubernetes_dev:

Local Kubernetes Development
============================

This guide runs the full Nopayloaddb stack (Django + pgbouncer + nginx + PostgreSQL) on a
local cluster using the official Helm charts. Two platforms are supported:

- **Minikube** (standard Kubernetes) — requires Docker, ``minikube``, ``kubectl``, Helm 3.
  The charts need small modifications (see below).
- **OpenShift Local** (CRC) — requires ``crc``, the ``oc`` CLI, Helm 3. The charts work
  as-is.

The steps are the same on both platforms unless noted. ``kubectl`` and ``oc`` are
interchangeable for the commands below.

1. Start a Local Cluster
------------------------

**Minikube:**

.. code-block:: bash

   minikube start --driver=docker --cpus=4 --memory=8192
   minikube addons enable ingress
   kubectl get nodes            # verify the cluster is up
   minikube dashboard --url     # optional web dashboard

**OpenShift Local:**

.. code-block:: bash

   crc start
   eval $(crc oc-env)
   oc login -u developer -p developer https://api.crc.testing:6443
   oc get nodes                 # verify the cluster is up
   crc console --url            # optional web console (developer/developer)

2. Prepare the Helm Charts
--------------------------

.. code-block:: bash

   git clone https://github.com/BNLNPPS/nopayloaddb-charts.git
   cd nopayloaddb-charts

The charts are written for OpenShift and use two OpenShift-only resources:
``ImageStream`` (use plain Docker images on Kubernetes instead) and ``Route`` (use an
``Ingress`` on Kubernetes instead).

**OpenShift Local users can skip ahead to step 3.** For **Minikube**, create a
Kubernetes-compatible copy of the chart:

.. code-block:: bash

   cp -r nopayloaddb nopayloaddb-k8s
   cd nopayloaddb-k8s

   # Remove the ImageStream blocks (lines 1-15 of each file)
   sed -i '1,15d' templates/django.yaml
   sed -i '1,15d' templates/pgbouncer.yaml

   # Replace the OpenShift Route (lines 111-124) with a Kubernetes Ingress
   sed -i '111,124d' templates/nginx.yaml
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

Then create a values file. The same content works on both platforms — only ``domain``
differs (``minikube.local`` for Minikube, ``apps-crc.testing`` for OpenShift Local):

.. code-block:: yaml

   # values-local.yaml
   domain: minikube.local          # apps-crc.testing on OpenShift Local
   project: nopayloaddb-dev
   appname: nopayloaddb-dev

   # Database parameters (matching the PostgreSQL deployed in step 3)
   dbhost: postgresql
   dbname: nopayloaddb
   dbuser: npdb
   dbpassword: dev_password

   # Log paths
   django_logpath: /tmp/logs
   nginx_logpath: /tmp/logs
   pgbouncer_logpath: /tmp/logs

   # Persistent Volume Claim (created in step 4)
   pvcname: nopayloaddb-pvc

   # Docker images. Note: ghcr.io/plexoos/npdb is x86_64-only;
   # see Troubleshooting below for ARM64 / Apple Silicon.
   django_docker_image: ghcr.io/plexoos/npdb
   django_docker_image_tag: latest
   pgbouncer_docker_image: pgbouncer/pgbouncer
   pgbouncer_docker_image_tag: latest

3. Deploy PostgreSQL
--------------------

.. code-block:: bash

   kubectl create namespace nopayloaddb-dev      # oc new-project nopayloaddb-dev

   helm repo add bitnami https://charts.bitnami.com/bitnami
   helm repo update

   helm install postgresql bitnami/postgresql \
     --namespace nopayloaddb-dev \
     --set auth.postgresPassword=admin_password \
     --set auth.username=npdb \
     --set auth.password=dev_password \
     --set auth.database=nopayloaddb \
     --set persistence.enabled=true \
     --set persistence.size=10Gi

   kubectl wait --for=condition=ready pod \
     -l app.kubernetes.io/name=postgresql -n nopayloaddb-dev --timeout=300s

4. Create the Application PVC
-----------------------------

.. code-block:: bash

   kubectl apply -n nopayloaddb-dev -f - << 'EOF'
   apiVersion: v1
   kind: PersistentVolumeClaim
   metadata:
     name: nopayloaddb-pvc
   spec:
     accessModes:
       - ReadWriteOnce
     resources:
       requests:
         storage: 5Gi
   EOF

5. Deploy Nopayloaddb
---------------------

Use the modified chart directory on Minikube (``./nopayloaddb-k8s``) or the original one on
OpenShift Local (``./nopayloaddb``):

.. code-block:: bash

   helm install nopayloaddb ./nopayloaddb-k8s \
     --namespace nopayloaddb-dev \
     --values values-local.yaml

   kubectl wait --for=condition=available deployment/django \
     -n nopayloaddb-dev --timeout=300s
   kubectl get pods -n nopayloaddb-dev

6. Access the Application
-------------------------

The simplest option on both platforms is a port forward:

.. code-block:: bash

   kubectl port-forward service/nginx 8080:8080 -n nopayloaddb-dev
   curl http://localhost:8080/api/cdb_rest/gt

Alternatives:

- **Minikube**: ``minikube service nginx -n nopayloaddb-dev --url``, or use the Ingress by
  adding ``$(minikube ip) nopayloaddb-dev.minikube.local`` to ``/etc/hosts``.
- **OpenShift Local**: ``oc get routes -n nopayloaddb-dev`` and open the route URL.

7. Initialize the Database
--------------------------

.. code-block:: bash

   kubectl exec -it deployment/django -n nopayloaddb-dev -- python manage.py migrate
   kubectl exec -it deployment/django -n nopayloaddb-dev -- python manage.py createsuperuser

Day-to-Day Workflow
-------------------

.. code-block:: bash

   # Application and database logs
   kubectl logs -f deployment/django -n nopayloaddb-dev
   kubectl logs -f statefulset/postgresql -n nopayloaddb-dev

   # Django shell inside the pod
   kubectl exec -it deployment/django -n nopayloaddb-dev -- python manage.py shell

   # Restart after changes
   kubectl rollout restart deployment/django -n nopayloaddb-dev

   # Apply chart/values changes
   helm upgrade nopayloaddb ./nopayloaddb-k8s \
     --namespace nopayloaddb-dev --values values-local.yaml

Cleanup
-------

.. code-block:: bash

   helm uninstall nopayloaddb -n nopayloaddb-dev
   helm uninstall postgresql -n nopayloaddb-dev
   kubectl delete namespace nopayloaddb-dev   # oc delete project nopayloaddb-dev

   # Stop / remove the local cluster
   minikube stop        # or: crc stop
   minikube delete      # or: crc delete

Troubleshooting
---------------

- **``ImageStream``/``Route`` errors on Minikube** — you are deploying the original
  OpenShift chart on standard Kubernetes; use the modified copy from step 2.
- **``ImagePullBackOff`` on ARM64 / Apple Silicon** — ``ghcr.io/plexoos/npdb`` is built for
  x86_64 only. Either run under emulation (slower), or build your own image and point the
  values file at it:

  .. code-block:: bash

     git clone https://github.com/BNLNPPS/nopayloaddb.git
     cd nopayloaddb
     docker build --platform linux/arm64 -t nopayloaddb:arm64-local .

- **Pod not starting** — ``kubectl describe pod <pod-name> -n nopayloaddb-dev``.
- **Database connection errors** — check that the PostgreSQL pod is ready and that the
  credentials in your values file match step 3:
  ``kubectl logs -l app.kubernetes.io/name=postgresql -n nopayloaddb-dev``.
- **Storage issues** — ``kubectl get pvc -n nopayloaddb-dev``.
- **nginx service not reachable** — ``kubectl get svc,endpoints nginx -n nopayloaddb-dev``.
