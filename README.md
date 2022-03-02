## Current release 

Current release tag is 0.0.6

```shell
git clone --depth 1 --branch 0.0.6 https://github.com/BNLNPPS/nopayloaddb /nopayloaddb
```

This release will be deployed at Production and Tests instances when OKD will back

Production:
```
http://nopayloaddb-nopayloaddb.apps.sdcc.bnl.gov
```

Test:
```
http://npdb-test-test.apps.sdcc.bnl.gov
```

Example of read call to get last Payload for Global tag "sPHENIX_ExampleGT_24" and IOV=999999:
```
[spool0001] /usatlas/u/hollowec/oc > curl 'http://npdb-test-test.apps.sdcc.bnl.gov/api/cdb_rest/payloadiovs/?gtName=sPHENIX_ExampleGT_24&majorIOV=0&minorIOV=999999'
[{"id":210,"name":"Beam_210","global_tag":"sPHENIX_ExampleGT_24","payload_type":"Beam","payload_iov":[{"id":13425388,"payload_url":"D0DXMagnets.dat","major_iov":0,"minor_iov":999999,"payload_list":"Beam_210","created":"2022-02-21T15:28:20.949696"}],"created":"2022-02-21T15:17:06.481186"},{"id":211,"name":"FieldMap_211","global_tag":"sPHENIX_ExampleGT_24","payload_type":"FieldMap","payload_iov":[{"id":14834648,"payload_url":"sphenix3dbigmapxyz.root","major_iov":0,"minor_iov":999999,"payload_list":"FieldMap_211","created":"2022-02-21T15:46:04.757164"}],"created":"2022-02-21T15:17:06.494165"},{"id":212,"name":"CEMC_Thresh_212","global_tag":"sPHENIX_ExampleGT_24","payload_type":"CEMC_Thresh","payload_iov":[{"id":14364215,"payload_url":"CEMCprof_Thresh30MeV.root","major_iov":0,"minor_iov":999999,"payload_list":"CEMC_Thresh_212","created":"2022-02-21T15:39:58.850698"}],"created":"2022-02-21T15:17:06.507635"},{"id":213,"name":"ZDC_213","global_tag":"sPHENIX_ExampleGT_24","payload_type":"ZDC","payload_iov":[{"id":12975395,"payload_url":"towerMap_ZDC.txt","major_iov":0,"minor_iov":999999,"payload_list":"ZDC_213","created":"2022-02-21T15:23:17.996134"}],"created":"2022-02-21T15:17:06.520845"},{"id":214,"name":"CEMC_Geo_214","global_tag":"sPHENIX_ExampleGT_24","payload_type":"CEMC_Geo","payload_iov":[{"id":13925399,"payload_url":"cemc_geoparams-0-0-4294967295-1536789215.xml","major_iov":0,"minor_iov":999999,"payload_list":"CEMC_Geo_214","created":"2022-02-21T15:34:56.762293"}],"created":"2022-02-21T15:17:06.535601"}]
```

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
