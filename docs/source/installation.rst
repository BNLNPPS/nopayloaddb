.. _install:

Installation
============

This guide provides instructions on how to set up the Nopayloaddb project for development or deployment. You can choose between a manual setup or using Docker Compose (recommended for development).

Manual Installation
-------------------

Follow these steps for a traditional manual setup.

**Prerequisites:**

*   **Python:** Version 3.8 or higher is recommended (Python 3.9 is used in the Dockerfile).
*   **pip:** Python package installer.
*   **Git:** Version control system.
*   **PostgreSQL:** Database server. Ensure the `psycopg` build prerequisites are met (e.g., `libpq-dev` and `python3-dev` on Debian/Ubuntu, `postgresql-devel` and `python3-devel` on Fedora/CentOS). Check the `psycopg` documentation for details.

**Steps:**

1.  **Clone the Repository:**
    .. code-block:: bash

       git clone <repository-url>  # Replace <repository-url> with the actual URL
       cd nopayloaddb

2.  **Virtual Environment:**
    It is highly recommended to use a virtual environment:
    .. code-block:: bash

       python -m venv venv
       source venv/bin/activate  # On Windows use `venv\Scripts\activate`

3.  **Install Dependencies:**
    Install requirements using pip:
    .. code-block:: bash

       pip install -r requirements.txt

4.  **Database Setup:**
    *   **Create PostgreSQL Databases and Users:** Log in to your PostgreSQL server. The application is configured in `nopayloaddb/settings.py` to use separate write (`default`) and read replica databases (`read_db_1`, `read_db_2`). You'll need to create the database(s) and user(s) accordingly.

        *Example for the write database:*
        .. code-block:: sql

           -- Replace 'dbname_w', 'login_w', 'password_w' with your desired values
           CREATE DATABASE dbname_w;
           CREATE USER login_w WITH PASSWORD 'password_w';
           GRANT ALL PRIVILEGES ON DATABASE dbname_w TO login_w;
           -- Optional, may be needed on some systems:
           -- ALTER ROLE login_w CREATEDB;

        Repeat the process or configure PostgreSQL replication for the read databases (`dbname_r1`, `dbname_r2`) and create corresponding read-only users (`login_r1`, `login_r2`) if you intend to use the read replica feature. For simple development, you can configure all `DATABASES` entries in `settings.py` to point to the same database, but ensure the environment variables match.

    *   **Run Migrations:** Apply the database schema migrations using the `default` (write) database connection. Make sure your environment variables for the write database are set correctly first (see Configuration section).
        .. code-block:: bash

           # Ensure environment variables are set (e.g., source .env)
           python manage.py migrate

5.  **Configuration:**
    The application relies heavily on environment variables, defined in `nopayloaddb/settings.py`.

    *   **Essential Variables:**
        *   `SECRET_KEY`: **Required.** A unique, secret key. The default `'changetosomething'` in `settings.py` is **insecure** and must be overridden.
        *   `DJANGO_LOGPATH`: Path for log files (defaults to `/var/log`). Ensure write permissions.

    *   **Database Variables:** Specific variables are expected for write (`_W`) and read replicas (`_R1`, `_R2`):
        *   `POSTGRES_DB_W`, `POSTGRES_USER_W`, `POSTGRES_PASSWORD_W`, `POSTGRES_HOST_W`, `POSTGRES_PORT_W`
        *   `POSTGRES_DB_R1`, `POSTGRES_USER_R1`, `POSTGRES_PASSWORD_R1`, `POSTGRES_HOST_R1`, `POSTGRES_PORT_R1`
        *   `POSTGRES_DB_R2`, `POSTGRES_USER_R2`, `POSTGRES_PASSWORD_R2`, `POSTGRES_HOST_R2`, `POSTGRES_PORT_R2`

    *   **Setting Environment Variables:**
        *   **Directly in shell:** (Temporary)
          .. code-block:: bash

             export SECRET_KEY='your-very-strong-secret-key'
             export POSTGRES_DB_W='dbname_w'
             # ... etc.

        *   **Using `.env` file:** Create/modify `.env` in the project root. **Important:** The example `.env` provided uses generic names (e.g., `POSTGRES_DB`). You **must** update it to use the specific names from `settings.py` (e.g., `POSTGRES_DB_W`). Use `export KEY=VALUE` format if you plan to load variables using `source .env`.

          *Example `.env` for manual setup (using `source`):*
          .. code-block:: bash

             export SECRET_KEY='your-very-strong-secret-key'
             export DJANGO_LOGPATH='/path/to/your/logs'

             export POSTGRES_DB_W=dbname_w
             export POSTGRES_USER_W=login_w
             export POSTGRES_PASSWORD_W=password_w
             export POSTGRES_HOST_W=localhost
             export POSTGRES_PORT_W=5432

             # Add R1/R2 variables if using read replicas
             # export POSTGRES_DB_R1=dbname_r1
             # ... etc.

          Load variables before running commands:
          .. code-block:: bash

             source .env
             python manage.py migrate
             python manage.py runserver

        *   **Deployment System:** Use systemd, Kubernetes secrets, etc. for production.

6.  **Running the Development Server:**
    Ensure environment variables are loaded:
    .. code-block:: bash

       # Example: source .env
       python manage.py runserver

    Access at `http://127.0.0.1:8000/`.


Using Docker Compose (Recommended for Development)
--------------------------------------------------

The project includes `Dockerfile` and `docker-compose.yml` for a containerized setup.

**Prerequisites:**

*   **Docker:** Install Docker Desktop (Windows, macOS) or Docker Engine (Linux).
*   **Docker Compose:** Usually included with Docker Desktop, or install separately.

**Steps:**

1.  **Clone the Repository:** (If you haven't already)
    .. code-block:: bash

       git clone <repository-url>
       cd nopayloaddb

2.  **Configure Environment Variables (`.env`):**
    `docker-compose.yml` loads variables from the `.env` file. **Crucially**, ensure the variables match those expected by `nopayloaddb/settings.py`. Use `KEY=VALUE` format (no `export` needed for Docker Compose).

    *   **Rename variables:** Change generic names (e.g., `POSTGRES_DB`) to specific ones (e.g., `POSTGRES_DB_W`).
    *   **Set `POSTGRES_HOST_W`:** Set `POSTGRES_HOST_W=db` (matches the database service name in `docker-compose.yml`).
    *   **Add `SECRET_KEY`:** Add a `SECRET_KEY` variable.
    *   **Add Read Replicas (Optional):** Add `POSTGRES_*_R1` and `POSTGRES_*_R2` variables if needed. Note: The default `docker-compose.yml` only sets up one database service (`db`). You would need to modify it to add replica services and configure replication.
    *   **Add `DJANGO_LOGPATH` (Optional):** Set `DJANGO_LOGPATH` (e.g., `/npdb/logs`).

    *Example `.env` for Docker Compose:*
    .. code-block:: bash

       # Use KEY=VALUE format
       SECRET_KEY='your-development-secret-key'
       DJANGO_LOGPATH='/npdb/logs' # Example path inside container

       # Write Database (_W variables matching settings.py)
       POSTGRES_DB_W=dbname
       POSTGRES_USER_W=login
       POSTGRES_PASSWORD_W=password
       POSTGRES_HOST_W=db # Service name from docker-compose.yml
       POSTGRES_PORT_W=5432

       # Optional: Add R1/R2 variables if needed and configured
       # POSTGRES_DB_R1=dbname
       # POSTGRES_USER_R1=login
       # ... etc.

3.  **Build and Run Containers:**
    From the project root directory:
    .. code-block:: bash

       docker-compose up --build -d # -d runs in detached mode

    This builds the `webapp` image, starts `db` and `webapp` services. The `webapp` service runs migrations and starts the development server automatically (see `command` in `docker-compose.yml`).

4.  **Access the Application:**
    Access at `http://localhost:8000` or `http://127.0.0.1:8000`.

5.  **View Logs:**
    .. code-block:: bash

       docker-compose logs -f webapp # Stream logs from webapp service

6.  **Stopping Containers:**
    .. code-block:: bash

       docker-compose down

    To remove containers and the database volume (deleting all data):
    .. code-block:: bash

       docker-compose down -v


Deployment
----------

For production environments:

*   **Do NOT use the Django development server (`runserver`) or `DEBUG = True`.**
*   Deploy using a production-grade WSGI server (Gunicorn, uWSGI) behind a reverse proxy (Nginx, Apache).
*   Set `DEBUG = False` in `settings.py`.
*   Ensure the `SECRET_KEY` environment variable is set securely.
*   Configure static file serving (`python manage.py collectstatic`).
*   Manage environment variables securely through your deployment system.
*   Consult the Django deployment checklist and documentation for your chosen components.
