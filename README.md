## How to start the services

The npdb web app can be built and started by using `docker-compose` within the
cloned repository:

```shell
docker-compose up --build
```

This option may be preferred for local development and tests. In order to stop
the services run the following command:

```shell
docker-compose down
```

The database and web services can be also started individually. The following
commands are essentially equivalent to the above procedure with `docker-compose`
and are shown here for the reference:

```shell
docker run --rm --env-file=.env --detach --name=pg --hostname=db -p 5432:5432 -v $PWD/db/data:/var/lib/postgresql/data postgres
docker run --rm --env-file=.env          --name=wa --link=pg -it -p 8000:8000 ghcr.io/plexoos/npdb:latest
```

During the development one may need to start over with empty DB tables. An easy
way to recreate the database tables is to remove the data directory:

```shell
rm -fr db/data
```

In order to deploy the npdb service on a Red Hat OpenShift (OKD) cluster we
recommend using the template provided in this repository. First, login into OKD:

```shell
oc login
```

Then create a new project if it does not exist yet:

```shell
oc new-project npps
```

Finally, register the new npdb template and start the web app from it:

```shell
oc create -f npdb_openshift_template.yaml
oc new-app --template=npdb
```
