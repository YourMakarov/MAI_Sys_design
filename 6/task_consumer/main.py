from confluent_kafka import Consumer
from pymongo import MongoClient
import json
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://mongo:mongo@mongodb:27017/task_tracker?authSource=admin")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

client = MongoClient(MONGODB_URL)
db = client.task_tracker

consumer = Consumer({
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'group.id': 'task_consumer',
    'auto.offset.reset': 'earliest'
})

consumer.subscribe(['tasks'])

try:
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            logger.error(f"Consumer error: {msg.error()}")
            continue
        try:
            data = json.loads(msg.value().decode('utf-8'))
            db.tasks.insert_one(data)
            logger.info(f"Inserted task: {data['task_id']}")
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
finally:
    consumer.close()
    client.close()