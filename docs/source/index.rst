.. nopayloaddbdoc nopayloaddb documentation master file

Nopayloaddb Documentation
==========================

The **Nopayloaddb** project serves as a reference implementation for a **Conditions Database (CDB)**, following guidelines and concepts relevant to the High Energy Physics (HEP) community, particularly those discussed within the HEP Software Foundation (HSF).

At its core, Nopayloaddb provides a **RESTful API** designed for managing and retrieving **conditions data**, often referred to as **payloads**. This data is typically time-dependent and associated with specific experimental conditions or configurations.

Key Concepts:
-------------

*   **Payloads:** The actual conditions data (e.g., calibration constants, alignment parameters) stored as binary large objects (BLOBs) or references to external files.
*   **Payload Type:** Defines the structure or category of a payload (e.g., 'BeamSpot', 'SiPixelQuality').
*   **Interval of Validity (IOV):** The time range (or other validity dimension, like run number) for which a specific payload is valid.
*   **Global Tag (GT):** A named collection of specific payload IOVs, representing a consistent set of conditions for a particular processing campaign or data-taking period.

The API allows clients (like experiment frameworks or analysis tools) to:

*   Upload new payloads and define their IOVs.
*   Create and manage payload types.
*   Assemble and manage Global Tags.
*   Query for the correct payloads based on a Global Tag and a specific time or run number.
*   Perform other administrative tasks like listing available Global Tags, payload types, etc.

This documentation provides details on installation, API usage, and the underlying data models and views.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   api

.. toctree::
   :maxdepth: 1
   :caption: CDB Reference:

   cdb_models
   cdb_views

