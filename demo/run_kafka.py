from kafka import KafkaProducer


# Load data into kafka

path = "data/miranda.json"
logs, n = [], 5
with open(path, "r") as f:
    i = 0
    for log in f.readlines():
        logs.append(log.strip().encode())

        i += 1
        if i == n:
            break


producer = KafkaProducer(
        bootstrap_servers="localhost:9092",
        acks="all",
        retries=5,
    )


for msg in logs:
    future = producer.send("logs_miranda", msg)
    try:
        record_metadata = future.get(timeout=10)
    except Exception as e:
        print("send failed:", e)
    print("Send!")
