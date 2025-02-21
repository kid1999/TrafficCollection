# TrafficCollection
Collect traffic from GitHub

### Config
Modify system configuration files, such as project folder paths.

`config/config.ini`
```ini
[spider]
interface=eth0
page_timeout=120000
output_dir=/traffic/datas
```
`Dockerfile`
```dockerfile
WORKDIR /traffic
...
COPY . /traffic
```
`docker-compose.yml`
```yaml
version: "3.8"

services:
  traffic:
    container_name: traffic
    volumes:
      - /traffic/datas:/traffic/datas
```


### Deploy
deploy with docker-compose.
```shell
docker-compose build
```

### Run
```shell
docker-compose up
```

### Data Migration
```shell
tar -cJvf traffic.tar.xz /traffic/datas
```
Pack and compress, download form remote server.

`docker container prune`
`ulimit -n 65536`
`ulimit -n`