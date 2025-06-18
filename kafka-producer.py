import os
import time
import json
import base64
from kafka import KafkaProducer
from tqdm import tqdm

FOLDER_PATH = '/home/iryandae/kafka_2.13-3.7.0/FP/data/test/' 
TOPIC_NAME = 'raw-images' 
SLEEP_TIME = 1

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

print(f"🚀 Sending images from {FOLDER_PATH} to Kafka topic '{TOPIC_NAME}'")

for filename in tqdm(sorted(os.listdir(FOLDER_PATH))):
    if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        continue

    file_path = os.path.join(FOLDER_PATH, filename)
    with open(file_path, 'rb') as f:
        img_bytes = f.read()
        img_b64 = base64.b64encode(img_bytes).decode('utf-8')

        message = {
            "filename": filename,
            "image": img_b64
        }

        producer.send(TOPIC_NAME, value=message)
        print(f"📤 Sent {filename}")
        time.sleep(SLEEP_TIME)  # simulate streaming

producer.flush()
print("✅ All images sent.")
