
## Start Kafka server

Use docker compose to start Kafka and Kafka-GUI.

```bash
docker compose up
```

Insert data in Kafka:
```bash
uv run demo/run_kafka.py
```

## Start Detectmate with Docker
(The network require some work)

### Start DetectMate Parser

Build the image:

```bash
docker build -f demo/Dockerfile.app1 -t detectmate-parser .
```

Run the image:
```bash
sudo docker run --name parser -d detectmate-parser
```

### Start DetectMate Detector

Build the image:

```bash
docker build -f demo/Dockerfile.app2 -t detectmate-detector .
```

Run the image:
```bash
sudo docker run --name detector -d detectmate-detector
```
