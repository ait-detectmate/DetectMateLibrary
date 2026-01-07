# Kafka Unitests

To run the kafka reader unit tests follow the next steps.

## Step 1: Initialize Kafka server
To start the server, we will use docker compose.
```bash
cd tests/test_readers/start_kafka

docker compose up
```
Check if is running in the UI using **http://localhost:8080/**.

## Step 2: Add messages
If and only if is the first time the kafka server was run, do the next command:
```bash
uv run add_messages.py
```

Check in the UI using **http://localhost:8080/** if the messages were added.


## Step 3: Remove the ignore test
Temporaly remove the **@pytest.mark.skip** from the kafka unittests in **test_reader_kafka.py**.

## Step 4: Run test
Run tests as normal pytests.
