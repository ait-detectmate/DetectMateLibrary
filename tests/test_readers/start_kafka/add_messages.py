from kafka import KafkaProducer

producer = KafkaProducer(
        bootstrap_servers="localhost:9092",
        acks="all",
        retries=5,
    )


for msg in [b"hello1", b"hello2", b"hello3"]:
    future = producer.send("test_topic", msg)
    try:
        record_metadata = future.get(timeout=10)
    except Exception as e:
        print("send failed:", e)
