.. nopayloaddb documentation master file

===================================
Nopayloaddb Documentation
===================================

**Nopayloaddb** is a reference implementation of a **Conditions Database (CDB)** for High Energy Physics (HEP) experiments, developed by the HEP Software Foundation (HSF). It provides a robust, scalable RESTful API for managing time-dependent calibration and configuration data.

.. warning::
   This documentation is under development. Some sections may be incomplete or not working as expected. Please report any issues on GitHub.

.. note::
   **Quick Start**: Ready to get started? Jump to our :doc:`installation` guide for Docker setup in under 5 minutes!

What is Nopayloaddb?
====================

Nopayloaddb serves as a **conditions database service** designed to handle the complex requirements of HEP experiments:

🔧 **Payload Management**
   Store and retrieve time-dependent calibration data, alignment parameters, and configuration settings

📊 **Version Control**
   Manage different versions of conditions data with proper validity intervals (IOVs)

🏷️ **Global Tags**  
   Organize consistent sets of conditions for specific processing campaigns or data-taking periods

🔄 **Read/Write Splitting**
   Scalable architecture with support for read replicas and database load balancing

🌐 **RESTful API**
   Clean, well-documented HTTP API for easy integration with experiment frameworks

Key Features
============

✨ **Ready to Adopt**
   - Docker containerization for easy deployment
   - PostgreSQL backend with connection pooling
   - Kubernetes and OpenShift deployment templates

🛡️ **Security & Performance**
   - JWT and token-based authentication
   - Bulk operations for efficient data loading
   - Comprehensive logging and monitoring (in development)

🔧 **Developer Friendly**
   - Django ORM with custom database routing
   - RESTful API built with Django REST Framework
   - Documentation and examples

Core Concepts
=============

Understanding these key concepts will help you work effectively with Nopayloaddb:

**Payloads**
   The actual conditions data (e.g., calibration constants, alignment parameters) stored as references to external files or binary data.

**Payload Types**
   Categories that define the structure or type of payload data (e.g., 'BeamSpot', 'SiPixelQuality', 'CEMC_Thresh').

**Interval of Validity (IOV)**
   The time range, run number range, or other validity dimension for which a specific payload is valid.

**Global Tags**
   Named collections of specific payload IOVs that represent a consistent set of conditions for a particular processing campaign or data-taking period.

**Payload Lists**
   Intermediate entities that link Global Tags to Payload Types, serving as containers for related payload versions.

Architecture Overview
=====================

.. mermaid::

   graph TD
       A["Client App<br/><small>Web/CLI Applications</small>"] 
       B["REST API<br/><small>Django Framework</small>"]
       C["PostgreSQL Database<br/><small>Metadata Storage</small>"]
       D["Payload Files<br/><small>External Storage</small>"]
       
       A <--> B
       B <--> C
       B <--> D
       
       classDef client fill:#e1f5fe,stroke:#0277bd,stroke-width:2px
       classDef api fill:#1565c0,stroke:#0d47a1,stroke-width:3px,color:#fff
       classDef database fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
       classDef storage fill:#f1f8e9,stroke:#388e3c,stroke-width:2px
       
       class A client
       class B api
       class C database
       class D storage


The system follows a **metadata-only** approach where the database stores references to payload files rather than the files themselves, enabling efficient storage and retrieval of large datasets.

Getting Started
===============

Choose your preferred installation method:

.. grid:: 1 2 2 2
   :gutter: 3

   .. grid-item-card:: 🚀 Quick Start
      :link: installation
      :link-type: doc

      Get up and running in minutes with Docker Compose. Perfect for trying out Nopayloaddb or development work.

      **Time:** 5 minutes  
      **Requirements:** Docker

   .. grid-item-card:: ⚙️ Manual Installation
      :link: installation
      :link-type: doc

      Full control installation for development or custom deployments.

      **Time:** 15-30 minutes  
      **Requirements:** Python, PostgreSQL

   .. grid-item-card:: 🏭 Production Deploy
      :link: deployment
      :link-type: doc

      Production-ready deployment with Kubernetes, OpenShift, or traditional servers. Includes official Helm charts for experiment-specific configurations.

      **Time:** 1+ hours  
      **Requirements:** Container orchestration  
      **Helm Charts:** `nopayloaddb-charts <https://github.com/BNLNPPS/nopayloaddb-charts>`_

   .. grid-item-card:: 🔧 Development Setup
      :link: development
      :link-type: doc

      Set up a development environment for contributing to Nopayloaddb.

      **Time:** 30 minutes  
      **Requirements:** Python, Git, PostgreSQL

Documentation Structure
=======================

This documentation is organized into several sections:

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   installation
   usage

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   api
   architecture

.. toctree::
   :maxdepth: 2
   :caption: Deployment & Development

   deployment
   development

.. toctree::
   :maxdepth: 1
   :caption: API Reference

   cdb_models
   cdb_views

API Quick Reference
===================

Here are some common API endpoints to get you started:

**Global Tags**

.. code-block:: bash

   # List all global tags
   curl http://localhost:8000/api/cdb_rest/globalTags

   # Get specific global tag
   curl http://localhost:8000/api/cdb_rest/globalTag/sPHENIX_ExampleGT_24

**Payload Queries**

.. code-block:: bash

   # Query payloads by global tag and IOV
   curl 'http://localhost:8000/api/cdb_rest/payloadiovs/?gtName=sPHENIX_ExampleGT_24&majorIOV=0&minorIOV=999999'

**Create Resources**

.. code-block:: bash

   # Create new global tag
   curl -X POST http://localhost:8000/api/cdb_rest/gt \
     -H "Content-Type: application/json" \
     -d '{"name": "MyNewGT", "author": "username", "description": "New global tag"}'

For complete API documentation, see :doc:`api`.

Example Use Cases
=================

**Experiment Calibration Management**
   Store and retrieve detector calibration constants that vary over time or run conditions.

**Configuration Management**
   Manage experiment configuration parameters for different data-taking periods.

**Simulation Conditions**
   Organize conditions data for Monte Carlo simulations with proper versioning.

**Data Processing Campaigns**
   Create consistent condition sets for large-scale data reprocessing efforts.

Community & Support
====================

**Getting Help**

- 📖 **Documentation**: You're reading it! Check out the specific guides for detailed information
- 🐛 **Issues**: Report bugs or request features on `GitHub Issues <https://github.com/BNLNPPS/nopayloaddb/issues>`_
- 💬 **Discussions**: Join the conversation in the HEP Software Foundation forums

**Contributing**

Nopayloaddb is an open-source project welcoming contributions:

- 🔧 **Code**: Submit pull requests for bug fixes or new features
- 📚 **Documentation**: Help improve these docs
- 🧪 **Testing**: Report bugs or help with testing
- 💡 **Ideas**: Suggest new features or improvements

See our :doc:`development` guide for details on contributing.

**License**

Nopayloaddb is released under an open-source license. See the project repository for details.

Project Status
==============

.. list-table::
   :widths: 20 80
   :header-rows: 0

   * - **Version**
     - 0.3 (Active Development)
   * - **Status**
     - Production Ready
   * - **Python**
     - 3.8+ (3.9+ recommended)
   * - **Django**
     - 4.x
   * - **Database**
     - PostgreSQL 12+ (13+ recommended)
   * - **Last Updated**
     - 2025

Acknowledgments
===============

Nopayloaddb is developed and maintained by the `HEP Software Foundation <https://hepsoftwarefoundation.org/>`_ community, with contributions from researchers and engineers across the high-energy physics community.

Special thanks to all contributors who have helped shape this project into a robust solution for conditions database management in HEP experiments.

---

.. note::
   **Next Steps**: Ready to start? Head over to the :doc:`installation` guide to get Nopayloaddb running, or check out the :doc:`usage` examples to see what you can do with it!