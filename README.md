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


**Group 1:**
- **aaronacuuna**: Aaron Acuña Bellido.
- **TachoPablo2**: Pablo Romero Gómez.
- **javiarellanoo**: Javier Arellano López.
- **RauruGW**: Raúl Calero Capote.
- **Alvaro1909**: Álvaro Barragán Bernal.
- **mpradoj04**: Miguel Prado Jiménez.

**Group 2:**
- **grnln**: Guillermo Rodríguez Narbona.
- **mquirosq**: María Quirós Quiroga.
- **PFerreria**: Pablo Ferrería Hijón.
- **daniherurb**: Daniel Herrera Urbano.
- **IMora04**: Ignacio Mora Pérez.
- **LuisGomezdeTerreros**: Luis Gómez de Terreros Oramas.

## Methodology
### Repository branching model
This repository uses a variation of *EGCFlow*, a methodology proposed by the lecturers of *EGC* in the *Universidad de Sevilla*. This methodology considers the following branches:
- `main`: Branch meant for final releases corresponding to the Milestones.
- `integration-trunk`: Branch used to integrate the code developed by G1 and G2.
- `trunk-g1`: Branch used to integrate the work produced by the members development group 1 (fitshub-1).
- `trunk-g2`: Branch used to integrate the work produced by the members development group 2 (fitshub-2).
- `ft/____`: Used to name any branch related to adding new features to the system, should be deleted after the work performed is complete.
- `bf/____`: Used to name any branch related to fixing bugs or incidents, should be deleted after the work performed is complete.

### Commit policy
This projects uses Convential Commits. A commit should have the following structure:

```
git commit -m"<type> (<optional scope>):  <description>" 
  -m"<optional body>" 
  -m"<optional footer>"
```

Where:
- **type**: Indicates the ctegory of the change (ex. feat, fix, refactor, test...).
- **scope** (op): Indicates the part of the project that is impacted.
- **description**: Short text that describes the change.
- **body** (op): Reason why the change was made.
- **footer** (op): Information regarding Breaking Changes and issue references.

### Versioning strategy
For versioning, we are using Semantic Versioning, with a version haveing the form: *X.Y.Z*. These mean:
- **X - Major**: Changes that break the public API compatibility.
- **Y - Minor**: Changes that don't break the public API compatibility.
- **Z - Patch**: Small changes that fix bugs.

### Issue templates
To create an issue, select the "New Issue" button in the Github UI. We have defined four issue templates:
- **Enhancement**: Used to provide a suggestion or enhancement for the application.
- **Incident**: Used to report a bug or incident found in the application.
- **Pipeline Task**: Used to add a task related to the CI/CD pipeline of the project.
- **Work Item**: Used to add a task related to new functionality that has been planed for the system.


## Deployment
The application is automatically deployed in render whne a push is made to either `main`, `integration-trunk`, `trunk-g1` or `trunk-g2`.
The render deployment is available at:
- https://fitshub.onrender.com (`main`)
- https://fitshub-dev.onrender.com (`integration-trunk`)
- https://fitshub-g1.onrender.com (`trunk-g1`)
- https://fitshub-g2.onrender.com (`trunk-g2`)

## Workflow notifications
This project contains a workflow that sends a notification through *Telegram* when a CI or CD workflow finishes its run to report its status. If you would like to participate, please contact the developers.


## Development environment

### NEW!

### Docker Compose

Spin up the full stack, including the ancillary Elasticsearch node used for search and Mailhog node for e-mail management:

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

Fitshub expects an instance of **Elasticsearch** to be running at port 9200, as well as an instance of **Mailhog** to be running at port 1025. In order for this feature to work, please follow the following steps:

- Copy the environment variables from ```.env.local.example``` into your ``.env`` and make sure that the variable ```ELASTICSEARCH_HOST```is set to ```http://localhost:9200```

- Start the instance of **Mailhog** in port 1025. To do so, run the following command:

``` bash 
docker compose -f ./docker/docker-compose.dev.yml up -d mailhog 
```


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