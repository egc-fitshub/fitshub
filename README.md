<div style="text-align: center;">
  <img src="/app/static/img/logos/logo.png" alt="Logo" width="200">
</div>

# fitshub<span>.io</span>

**fitshub<span>.io</span>** is a collaborative platform and repository of FITS (Flexible Image Transport System) models designed for astronomical databases.  
FITS is the standard format for storing, transmitting, and processing astronomical data, supporting multi-dimensional arrays and rich metadata such as photometric, spatial, and calibration information.

fitshub<span>.io</span> is a **fork of [uvlhub.io](https://uvlhub.io/)**, enhancing the original platform with new FITS models and additional functionality.  
The platform integrates a **Zenodo clone** for dataset management and the **AstroPy** library for data handling and analysis, promoting interoperability and reproducibility in astronomical research.  
By following **Open Science** principles, fitshub<span>.io</span> aims to provide a structured and accessible environment for sharing scientific data and models within the astronomy community.

This project is developed by the **FitsHub Project Teams 1 and 2** as the practical component of the **Evolución y Gestión de la Configuración (EGC)** course at the **University of Seville**.

## Development environment

### Docker Compose (recommended)

Spin up the full stack, including the new Elasticsearch node used for search:

```bash
docker compose -f docker/docker-compose.dev.yml up -d
```
Once the containers are running you can check Elasticsearch health from your host machine:

```bash
curl http://localhost:9200/_cluster/health
```

A response with `status` set to `green` or `yellow` means the search cluster is ready. The explore UI will show real search results when this service is available, and a friendly message if it is down.

### Using Virtual Environment

> [!WARNING]
> To complete the configuration succesfully, it is important that all dependencies, as well as your database, are up to date.

Fitshub expects an instance of **Elasticsearch** to be running at port 9200. In order for this feature to work, please follow the following steps:

- Copy the environment variables from ```.env.local.example``` into your ``.env`` and make sure that the variable ```ELASTICSEARCH_HOST```is set to ```http://localhost:9200```
- Start the instance of **Elasticsearch** in port 9200. To do so, run the following command: 

``` bash 
docker compose -f ./docker/docker-compose.dev.yml up -d elasticsearch 
```

- Once the container is available, please run the following command to check its status:
```bash
curl http://localhost:9200/_cluster/health
```

- If the result of the previous command returns **green**, execute the following command: 
```bash
flask shell
```
- Inside flask shell, run the following instructions:

```python

from app.modules.elasticsearch.utils import init_search_index, reindex_all

init_search_index()
reindex_all()
exit()

```

- Once the instructions have been executed succesfully, you may start your project as usual.



