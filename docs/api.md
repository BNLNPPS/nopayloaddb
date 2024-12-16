
# API Documentation

## Overview

The `nopayloaddb` project provides a RESTful API for managing payloads, global tags, payload types, and associated data. The API allows clients to perform CRUD operations on these resources.

## Base URL

All API endpoints are prefixed with `/api/cdb_rest/`.

---

## Endpoints

### 1. Create a New Payload IOV

#### Base URL

- **Endpoint**: `/api/cdb_rest/piov`

#### HTTP Method: `POST`

- **Description**: Creates a new Payload IOV with validation for logical IOV ranges and automatic calculations for `major_iov_end` and `minor_iov_end` if not provided.

- **Request Body**:
  ```json
  {
    "major_iov": 1000,
    "minor_iov": 2000,
    "major_iov_end": 3000,
    "minor_iov_end": 4000,
    "payload_url": "https://example.com/payload/1",
    "checksum": "e99a18c428cb38d5f260853678922e03"
  }
  ```
  - If `major_iov_end` or `minor_iov_end` is not provided, they are set to `sys.maxsize`.
  - A composite IOV (`comb_iov`) is calculated as:
    ```python
    comb_iov = major_iov + (minor_iov / 10 ** 19)
    ```

- **Validation**:
  - `major_iov_end` must be greater than or equal to `major_iov`.
  - If `major_iov_end` equals `major_iov`, `minor_iov_end` must be greater than `minor_iov`.

- **Error Response**:
  - **Condition**: Invalid IOV ranges.
  - **Response**:
    ```json
    {
      "detail": "PayloadIOV ending IOVs should be greater or equal than starting. Provided end IOVs: major_iov: 1000 major_iov_end: 500 minor_iov: 2000 minor_iov_end: 1000"
    }
    ```
  - **Status Code**: `500 INTERNAL SERVER ERROR`

- **Success Response**:
  ```json
  {
    "id": 1,
    "major_iov": 1000,
    "minor_iov": 2000,
    "comb_iov": "1000.00000000000002",
    "major_iov_end": 3000,
    "minor_iov_end": 4000,
    "payload_url": "https://example.com/payload/1",
    "checksum": "e99a18c428cb38d5f260853678922e03"
  }
  ```

---

### 2. Retrieve a Specific Payload IOV

#### Base URL

- **Endpoint**: `/api/cdb_rest/piov/<int:pk>`

#### HTTP Method: `GET`

- **Description**: Retrieves details of a specific Payload IOV identified by its primary key (`pk`).

- **URL Parameters**:
  - `<int:pk>` (integer, required): The primary key of the Payload IOV to retrieve.

- **Response Example**:
  - **Success**:
    ```json
    {
      "id": 1,
      "major_iov": 1000,
      "minor_iov": 2000,
      "comb_iov": "1000.00000000000002",
      "major_iov_end": 3000,
      "minor_iov_end": 4000,
      "payload_url": "https://example.com/payload/1",
      "checksum": "e99a18c428cb38d5f260853678922e03"
    }
    ```

  - **Error**:
    - **Condition**: The requested `pk` does not exist.
    - **Response**:
      ```json
      {
        "detail": "Not found."
      }
      ```
    - **Status Code**: `404 NOT FOUND`

---

### 3. Attach a Payload IOV to a Payload List

#### Base URL

- **Endpoint**: `/api/cdb_rest/piov_attach`

#### HTTP Method: `PUT`

- **Description**: Attaches a Payload IOV to a specified Payload List and validates for overlapping IOVs.

- **Request Body**:
  ```json
  {
    "payload_list": "example_payload_list",
    "piov_id": 1
  }
  ```

- **Validation**:
  - Checks for overlapping IOVs if the associated Global Tag (GT) is locked.
  - Handles special cases for open-ended IOVs.

- **Error Response**:
  - **Condition**: Payload List or Payload IOV is not found.
  - **Response**:
    ```json
    {
      "detail": "PayloadList not found."
    }
    ```
  - **Status Code**: `500 INTERNAL SERVER ERROR`

  - **Condition**: Overlapping IOVs detected.
  - **Response**:
    ```json
    {
      "detail": "GT is LOCKED. You are attempting to insert IOV (major_iov,minor_iov,major_iov_end, minor_iov_end) (1000,2000,3000,4000). Conflicts with existing IOV example_payload_url (1000,2000,3000,4000)"
    }
    ```
  - **Status Code**: `500 INTERNAL SERVER ERROR`

- **Success Response**:
  ```json
  {
    "id": 1,
    "payload_list": "example_payload_list",
    "major_iov": 1000,
    "minor_iov": 2000,
    "major_iov_end": 3000,
    "minor_iov_end": 4000,
    "payload_url": "https://example.com/payload/1",
    "checksum": "e99a18c428cb38d5f260853678922e03"
  }
  ```
