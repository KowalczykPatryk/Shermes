# Neo4j Setup (Docker + Desktop)

This document describes how to run and manage Neo4j for the project using Docker and optionally Neo4j Desktop.

## Quick Start using Docker Compose (`docker-compose.yml`)

Start Neo4j:
```bash
docker compose up -d
```

On first run, this will:
- download Neo4j image
- create container
- initialize persistent volume

If you get:
```bash
permission denied while trying to connect to the docker API at unix:///var/run/docker.sock
```
Docker works as system daemon (root-owned) and access to it have:
- root
- users in docker group

To add user to docker group:
```bash
sudo usermod -aG docker $USER
newgrp docker
```

Stop container
```bash
docker compose stop
```

Start again
```bash
docker compose start
```

Remove container (keep data)
```bash
docker compose down
```

Remove everything (including database data)
```bash
docker compose down -v
```

## Access Neo4j

After starting container:
- Neo4j Browser UI -> http://localhost:7474
- Bolt connection (Python / drivers) -> bolt://localhost:7687

## Default credentials
username: neo4j  
password: password

You can change them in `docker-compose.yml`:
```YAML
NEO4J_AUTH: neo4j/your_password
```

## Data persistence

All graph data is stored in docker volume:

`neo4j_shermes_data/`

This ensures that container restart does not delete data.

## Docker Volume (Database Storage)

This project uses a Docker named volume to persist Neo4j database data.

What is a Docker volume?

A volume is a mechanism used by Docker to store data outside of a container’s lifecycle.
This means that even if the container is stopped, removed, or recreated, the data remains intact.

In this project:
```YAML
volumes:
  - neo4j_shermes_data:/data
```
Where is the data stored physically?

Docker manages the location automatically.

On Linux systems, the data is typically stored in:

`/var/lib/docker/volumes/neo4j_shermes_data/_data`

## Neo4j Desktop (optional)

If you prefer GUI app instead of Docker run this script:
```bash
./neo4j_desktop.sh
```
It runs desktop app located in the ```"$HOME/neo4j-desktop-2.1.4-x86_64.AppImage"```. The executable file can be download from https://neo4j.com/download/.