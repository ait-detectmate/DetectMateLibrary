# Quickstart

This quickstart shows how to process a log dataset (we use data from the [AIT Log Data Set V2.0](https://zenodo.org/records/5789064)).

## Tutorials

We developed three tutorials that show how to work with DetectMate using a few straightforward examples:

* [Run individually](./quickstart.md#run-individually): Execute each component separately within a script.
* [Run basic pipeline](./quickstart.md##run-basic-pipeline): Execute all types of components together in a simple pipeline.
* [Run expert pipeline](./quickstart.md#run-expert-pipeline): Execute all types of components using a [Redis](https://redis.io/) connector and multi-source logs as the input.

## Before you start

Before starting, follow the next steps in your work directory:

1. Copy the logs from in [here](https://github.com/ait-detectmate/DetectMateLibrary/blob/main/tests/test_data/audit.log) and the matching templates from [here](https://github.com/ait-detectmate/DetectMateLibrary/blob/main/tests/test_data/audit_templates.txt).

2. Install DetectMateLibrary dependency:

```bash
pip install detectmatelibrary
```

## Run individually

In the first example, we will execute the components one by one to better understand their functionality. You can follow the tutorial by copying and pasting the different code sections into your script.


### 0. Define configuration

First, we need to set up all the variables, such as the paths and the parameters used by the `DetectMate` methods. As shown below, all the methods can be initialized within the same dictionary. We will explain all the steps bellow.

```python
--8<-- "docs/examples/others/quickstart.py:config"
```

In this example, we will work with audit log data. The code below shows what the logs look like before they are processed.

```python
--8<-- "docs/examples/others/quickstart.py:other"
```

### 1. Parse the logs

By default, the logs are not parsed. To parse them, we first initialize a parser and then process the log lines.

```python
--8<-- "docs/examples/others/quickstart.py:parse"
```
Documentation of the [TemplateCppTreeMatcher](../parsers/template_tree_matcher.md).

### 2. Run the detectors
After parsing the logs, we can run the detectors to identify anomalies. In this example, we’ll use two detectors.

```python
--8<-- "docs/examples/others/quickstart.py:detectors"
```
Documentation of the [CharsetDetector](../detectors/charset.md) and [NewValueDetector](../detectors/new_value.md).

### 3. Run the alert aggregation

Finally, to combine all the alerts collected from the various detectors, an alert aggregation method is executed. This is the final output of `DetectMate`.

```python
--8<-- "docs/examples/others/quickstart.py:aggregator"
```

## Run basic pipeline

Although you can run each method separately to gain more control over the individual steps, it isn’t required. You can also execute everything together as a single pipeline. Next, we will run the methods described earlier using the generic DetectMateLibray pipeline.

### 1. Initialize the pipeline

First, we initialze the pipeline.

```python
--8<-- "docs/examples/others/quickstart.py:pipeline"
```
Documentation of the [Pipeline](../pipeline.md).

### 2. Run the pipeline

Finally, we run the pipeline.

```python
--8<-- "docs/examples/others/quickstart.py:pipeline_run"
```

## Run expert pipeline

The earlier pipeline processes only a single log data source, and intermediate schemas are discarded, while any output is saved permanently. In this example, two log sources will run at the same time, and the detector and alert-aggregation outputs will be stored in a Redis service.

For this use case, we also need to download other types of logs, including downloading and adding these [Apache logs](https://github.com/ait-detectmate/DetectMateLibrary/blob/main/tests/test_data/apache.log).

### 0. Prepare logs

First, we will prepare the data. In this example, we will simply upload the Audit and Apache datasets and ensure they have distinct log sources.

```python
--8<-- "docs/examples/others/quickstart_2.py:prepare"
```

### 1. Prepare Redis

In this example, we’ll set up a Redis service using Docker Compose. Create a Docker Compose file named `compose.yaml` and add the following services.

```yaml
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

```bash
docker compose up -d
```

To reach the dashboard, launch your preferred web browser and navigate to the following URL:

```text
http://localhost:5540/
```

### 3. Initialize the pipeline

Now that the data and services are in place, we can return to our script and implement our pipeline. Previously, we relied on a dictionary to initialize the methods within the pipeline. In this case, we’ll use the Config classes instead. We will run two parsers—one for each log source—and four detectors, again two per source.

To link where the data should go, we first use the `log_source` argument in the parsers to specify which type of logs to process. For detectors, the `parser` argument is used to indicate which parser to pull data from.

We will store the alert data so that dataset 0 contains Audit alerts, dataset 1 contains Apache alerts, and dataset 2 contains all aggregated alerts.

```python
--8<-- "docs/examples/others/quickstart_2.py:initialize"
```

### 4. Run pipeline

Let’s execute the full pipeline to retrieve the data.

```python
--8<-- "docs/examples/others/quickstart_2.py:run"
```

### 5. Get the data

To retrieve the data, we can simply initialize the schemas using the various IDs.

```python
--8<-- "docs/examples/others/quickstart_2.py:get_data"
```
Documentation of the [Schemas](../schemas.md).

Or check the dashboard:

```text
http://localhost:5540/
```
