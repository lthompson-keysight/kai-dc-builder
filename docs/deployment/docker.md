# Running the DSE Controller via Docker Run

Use this example to run the KAI Data Center Builder via Docker Run.

## Parameters

We recommend managing parameters for Docker via an environment file `.env`. Read [Configure](configure.md) section on how to create and modify the `.env` file.

To use the commands below, initialize the environment variables:

```bash
source "${REPODIR}/aidc/.env"
```

## Starting

To start the controller, use

```bash
docker run --rm -d \
    --name ${DSE_DOCKER_NAME} \
    -p ${WEBUI}:443 \
    -p ${GRPC}:50001 \
    -v ${STORAGE}:/var/lib/dse \
    ${DSE_DOCKER_IMAGE} \
    --accept_eula \
    --server_name ${SERVER_NAME} \
    --user_name ${USER} \
    --db_name ${DB_NAME} \
    ${DATA_URL} \
    ${LICENSE_SERVERS} \
    ${FEATURES} \
    ${PLUGINS}
```

To display logs

```bash
docker logs -f "${DSE_DOCKER_NAME}"
```

## Stopping

```bash
docker stop "${DSE_DOCKER_NAME}"
```
