# Nopayloaddb

An implementation of the Conditions Database (CDB) for the [HEP Software Foundation](https://hepsoftwarefoundation.org/). It provides a RESTful API for managing global tags, payload types, payload lists, payload IOVs (Intervals of Validity), and associated metadata. The API supports full CRUD operations and is designed for high-energy physics experiment workflows.

## Features

- Global tag management with status transitions (unlocked, locked, frozen)
- Payload type and payload list associations
- IOV-based payload versioning (continuous and discrete modes)
- Configurable JWT authentication for write operations
- Pluggable permission system
- Read replica database routing for scalability

## Current Release

```shell
git clone --depth 1 --branch v5.0.0 https://github.com/BNLNPPS/nopayloaddb /nopayloaddb
```

## API Usage Examples

### List all global tags

```shell
curl '<BASE_URL>/api/cdb_rest/globalTags'
```

### Get payload IOVs for a global tag

```shell
curl '<BASE_URL>/api/cdb_rest/payloadiovs/?gtName=ExampleGT&majorIOV=0&minorIOV=999999'
```

Append `&shape=dict` to receive named fields instead of positional rows.

### Create a global tag (requires JWT authentication when `CDB_AUTH_CLASS` is set)

```shell
curl -X POST '<BASE_URL>/api/cdb_rest/gt' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <JWT_TOKEN>' \
  -d '{"name": "MyNewGlobalTag", "status": "unlocked"}'
```

### Check CDB configuration

Any `CDB_*` environment variable set on the server can be read back:

```shell
curl '<BASE_URL>/api/cdb_rest/user_settings/<SETTING_NAME>/'
```

## How to Start the Services

### Using Docker Compose (recommended for local development)

```shell
docker-compose up --build
```

To stop the services:

```shell
docker-compose down
```

To start fresh with empty database tables, remove the data directory and restart:

```shell
rm -fr db/data
docker-compose up --build
```

### Using Docker individually

```shell
docker run --rm --env-file=.env --detach --name=pg --hostname=db -p 5432:5432 -v $PWD/db/data:/var/lib/postgresql/data postgres
docker run --rm --env-file=.env --name=wa --link=pg -it -p 8000:8000 ghcr.io/bnlnpps/nopayloaddb:v5.0.0
```

## Configuration

The application is configured via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `JWT_SECRET` | Secret key for JWT token verification | `changetosomething` |
| `CDB_AUTH_CLASS` | Authentication class for write operations. Empty by default to allow all requests. | *(empty)* |
| `CDB_PERMISSION_PLUGIN_CLASS` | Permission plugin class | `cdb_rest.permissions_plugins.dummy.DummyPermissionPlugin` |
| `CDB_IOV_MODE` | IOV mode: `continuous` or `discrete` | `continuous` |
| `POSTGRES_DB_W` | Write database name | `dbname` |
| `POSTGRES_USER_W` | Write database user | `login` |
| `POSTGRES_PASSWORD_W` | Write database password | `password` |
| `POSTGRES_HOST_W` | Write database host | `localhost` |
| `POSTGRES_PORT_W` | Write database port | `5432` |

Read replicas are configured with `_R1` and `_R2` suffixes (e.g., `POSTGRES_DB_R1`, `POSTGRES_HOST_R2`).

### Enabling JWT Authentication

Set the authentication class to enable JWT-based auth for all write operations (POST, PUT, PATCH, DELETE). Read operations remain anonymous.

```shell
export CDB_AUTH_CLASS=cdb_rest.authentication.CustomJWTAuthentication
export JWT_SECRET=your-secret-key
```

## Deployment on OpenShift (OKD)

```shell
oc login
oc new-project npps
oc create -f npdb_openshift_template.yaml
oc new-app --template=npdb
```

## License

See [LICENSE](LICENSE) for details.
