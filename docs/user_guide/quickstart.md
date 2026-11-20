# Quickstart

This quickstart shows how to process logs from the AIT Log Data Set V2.0. [Dataset](https://zenodo.org/records/5789064)

## Tutorials

We developed three tutorials that show how to work with DetectMate using a few straightforward examples:

* Execute each component separately in a script. [Run individually](#run-individually)
* Run all component types together in one pipeline. [Run basic pipeline](#run-basic-pipeline)
* Process multiple log sources and store results with a Redis connector. [Run expert pipeline](#run-expert-pipeline)
* Run DetectMate through the Service. [Service tutorial](https://ait-detectmate.github.io/DetectMateService/latest/)

## Before you start

Set up your working directory before starting the tutorials.

1. Download the audit logs and their matching templates. [Audit logs](https://github.com/ait-detectmate/DetectMateLibrary/blob/main/tests/test_data/audit.log) · [Audit templates](https://github.com/ait-detectmate/DetectMateLibrary/blob/main/tests/test_data/audit_templates.txt)

2. Install the DetectMateLibrary package.

```console title="Install DetectMate"
pip install detectmatelibrary
```

## Run individually

In the first example, we will execute the components one by one to better understand their functionality. You can follow the tutorial by copying and pasting the different code sections into your script.


### 0. Define configuration

Define file paths and component parameters in one configuration dictionary.

```python title="Example configuration"
--8<-- "docs/examples/others/quickstart.py:config"
```

In this example, we will work with audit log data. The code below shows what the logs look like before they are processed.

```python title="Print the logs"
--8<-- "docs/examples/others/quickstart.py:other"
```

### 1. Parse the logs

By default, the logs are not parsed. To parse them, we first initialize a parser and then process the log lines.

```python title="Parse the logs"
--8<-- "docs/examples/others/quickstart.py:parse"
```
Documentation of the [TemplateCppTreeMatcher](../parsers/template_tree_matcher.md).

### 2. Run the detectors
After parsing the logs, we can run the detectors to identify anomalies. In this example, we’ll use two detectors.

```python title="Look for anomalies"
--8<-- "docs/examples/others/quickstart.py:detectors"
```
Documentation of the [CharsetDetector](../detectors/charset.md) and [NewValueDetector](../detectors/new_value.md).

### 3. Run the alert aggregation

Finally, to combine all the alerts collected from the various detectors, an alert aggregation method is executed. This is the final output of `DetectMate`.

```python title="Aggregate alerts"
--8<-- "docs/examples/others/quickstart.py:aggregator"
```

## Run basic pipeline

The DetectMateLibrary pipeline runs the components from the previous example together.

### 1. Initialize the pipeline

```python title="Initialize pipeline"
--8<-- "docs/examples/others/quickstart.py:pipeline"
```
Documentation of the [Pipeline](../pipeline.md).

### 2. Run the pipeline

Finally, we run the pipeline.

```python title="Run pipeline"
--8<-- "docs/examples/others/quickstart.py:pipeline_run"
```

## Run expert pipeline

The earlier pipeline processes only a single log data source, and intermediate schemas are discarded, while any output is saved permanently. In this example, two log sources will run at the same time, and the detector and alert-aggregation outputs will be stored in a Redis service.

Download the Apache logs as a second source. [Apache logs](https://github.com/ait-detectmate/DetectMateLibrary/blob/main/tests/test_data/apache.log)

### 0. Prepare logs

Load the Audit and Apache datasets and give each a distinct log source.

```python title="Prepare logs"
--8<-- "docs/examples/others/quickstart_2.py:prepare"
```

### 1. Prepare Redis

In this example, we’ll set up a Redis service using Docker Compose. Create a Docker Compose file named `compose.yaml` and add the following services.

```yaml title="Configure Redis service"
services:
  redis:
    image: redis:7-alpine
    container_name: redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    command: ["redis-server", "--appendonly", "yes"]
    volumes:
      - redis_data:/data

  redisinsight:
    image: redis/redisinsight:latest
    container_name: redisinsight
    restart: unless-stopped
    depends_on:
      - redis
    ports:
      - "5540:5540"
    environment:
      # Database 0
      RI_REDIS_HOST_0: redis
      RI_REDIS_PORT_0: "6379"
      RI_REDIS_ALIAS_0: local-db0
      RI_REDIS_DB_0: "0"

      # Database 1
      RI_REDIS_HOST_1: redis
      RI_REDIS_PORT_1: "6379"
      RI_REDIS_ALIAS_1: local-db1
      RI_REDIS_DB_1: "1"

      # Database 2
      RI_REDIS_HOST_2: redis
      RI_REDIS_PORT_2: "6379"
      RI_REDIS_ALIAS_2: local-db2
      RI_REDIS_DB_2: "2"
    volumes:
      - redisinsight_data:/data

volumes:
  redis_data:
  redisinsight_data:
```

Run it using the command below. After it starts up, you’ll be able to access the Redis dataset and the dashboard.

```console title="Run service"
docker compose up -d
```

To reach the dashboard, launch your preferred web browser and navigate to the following URL:

```console title="Access dashboard"
http://localhost:5540/
```

### 2. Initialize the pipeline

Now that the data and services are in place, we can return to our script and implement our pipeline. Previously, we relied on a dictionary to initialize the methods within the pipeline. In this case, we’ll use the Config classes instead. We will run two parsers—one for each log source—and four detectors, again two per source.

Set `log_source` on each parser to select its input logs. Set `parser` on each detector to select its input parser.

We will store the alert data so that dataset 0 contains Audit alerts, dataset 1 contains Apache alerts, and dataset 2 contains all aggregated alerts.

```python title="Initialize pipeline"
--8<-- "docs/examples/others/quickstart_2.py:initialize"
```

### 3. Run the pipeline

Let’s execute the full pipeline to retrieve the data.

```python title="Run pipeline"
--8<-- "docs/examples/others/quickstart_2.py:run"
```

### 4. Get the data

To retrieve the data, we can simply initialize the schemas using the various IDs.

```python title="Get data from Schema"
--8<-- "docs/examples/others/quickstart_2.py:get_data"
```
Documentation of the [Schemas](../schemas.md).

Or check the dashboard:

```console title="Access dashboard"
http://localhost:5540/
```
